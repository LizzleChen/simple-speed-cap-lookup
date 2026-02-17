import os
import sqlite3
import io
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from flask import Flask, jsonify, request, render_template

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent.parent
DB_PATH = DATA_DIR / "data.db"

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme")

ATYPE_LABELS = {1: "CBD", 2: "CBD Fringe", 3: "Urban", 4: "Suburban", 5: "Rural"}

PERIOD_HOURS = {"AM": 2, "Midday": 6, "PM": 4, "Night": 12, "Daily": 24}

# Special FUNCL=0 entries not in fc_ft
SPECIAL_FTYPES = {
    30: "Walk access connector",
    0: "Centroid connector",
}

app = Flask(__name__)


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def _get_conn():
    return sqlite3.connect(DB_PATH)


def _load_lookup():
    conn = _get_conn()
    df = pd.read_sql("SELECT * FROM speed_cap_lookup", conn)
    conn.close()
    for col in ["ATYPE", "FUNCL", "FTYPE", "POSTEDSP", "Speed", "HourlyCapacity"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _load_fcft():
    conn = _get_conn()
    df = pd.read_sql("SELECT * FROM fc_ft", conn)
    conn.close()
    return df


def _working_set():
    """Return TX-preferred lookup rows."""
    lookup = _load_lookup()
    tx = lookup[lookup["State"] == "TX"]
    all_rows = lookup[lookup["State"] == "All"]
    return pd.concat([tx, all_rows]).drop_duplicates()


def _funcl_to_ftypes():
    """Build FUNCL -> [(FTYPE, name), ...] mapping."""
    fcft = _load_fcft()
    mapping: dict[int, list[tuple[int, str]]] = {}
    for _, row in fcft.iterrows():
        fc = int(row["FNCL"])
        ft = int(row["FTYPE"])
        name = row["Roadway"]
        mapping.setdefault(fc, []).append((ft, name))
    for ft, desc in SPECIAL_FTYPES.items():
        mapping.setdefault(0, []).append((ft, desc))
    return mapping


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("lookup.html")


@app.route("/admin")
def admin():
    return render_template("admin.html")


# ---------------------------------------------------------------------------
# Lookup API
# ---------------------------------------------------------------------------
@app.route("/api/funcls")
def api_funcls():
    ftype = request.args.get("ftype", type=int)
    mapping = _funcl_to_ftypes()
    if ftype is not None:
        funcls = sorted(fc for fc, pairs in mapping.items()
                        if any(ft == ftype for ft, _ in pairs))
        return jsonify(funcls)
    return jsonify(sorted(mapping.keys()))


@app.route("/api/ftypes")
def api_ftypes():
    funcl = request.args.get("funcl", type=int)
    mapping = _funcl_to_ftypes()
    if funcl is not None and funcl in mapping:
        entries = sorted(mapping[funcl], key=lambda x: x[0])
    else:
        entries = sorted(
            [(ft, name) for lst in mapping.values() for ft, name in lst],
            key=lambda x: x[0],
        )
    return jsonify([{"ftype": ft, "name": name} for ft, name in entries])


@app.route("/api/atypes")
def api_atypes():
    funcl = request.args.get("funcl", type=int)
    ftype = request.args.get("ftype", type=int)
    working = _working_set()
    if ftype is not None:
        working = working[working["FTYPE"] == ftype]
    if funcl is not None:
        working = working[working["FUNCL"] == funcl]
    atypes = sorted(working["ATYPE"].dropna().unique().tolist())
    return jsonify([{"value": int(a), "label": ATYPE_LABELS.get(int(a), "Unknown")} for a in atypes])


@app.route("/api/speeds")
def api_speeds():
    funcl = request.args.get("funcl", type=int)
    ftype = request.args.get("ftype", type=int)
    atype = request.args.get("atype", type=int)
    working = _working_set()
    if ftype is not None:
        working = working[working["FTYPE"] == ftype]
    if funcl is not None:
        working = working[working["FUNCL"] == funcl]
    if atype is not None:
        working = working[working["ATYPE"] == atype]
    speeds = sorted(working["POSTEDSP"].dropna().unique().tolist())
    return jsonify([int(s) for s in speeds])


@app.route("/api/lookup")
def api_lookup():
    funcl = request.args.get("funcl", type=int)
    ftype = request.args.get("ftype", type=int)
    atype = request.args.get("atype", type=int)
    speed = request.args.get("speed", type=int)
    working = _working_set()
    if ftype is not None:
        working = working[working["FTYPE"] == ftype]
    if funcl is not None:
        working = working[working["FUNCL"] == funcl]
    if atype is not None:
        working = working[working["ATYPE"] == atype]
    if speed is not None:
        working = working[working["POSTEDSP"] == speed]
    if working.empty:
        return jsonify(None)
    row = working.iloc[0]
    return jsonify({
        "Speed": int(row["Speed"]),
        "HourlyCapacity": int(row["HourlyCapacity"]),
        "Alpha": float(row["Alpha"]),
        "Beta": float(row["Beta"]),
    })


# ---------------------------------------------------------------------------
# Admin API
# ---------------------------------------------------------------------------
@app.route("/api/admin/data")
def api_admin_data():
    if request.args.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    lookup = _load_lookup()
    return jsonify(lookup.to_dict(orient="records"))


@app.route("/api/admin/save", methods=["POST"])
def api_admin_save():
    body = request.get_json()
    if body.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    df = pd.DataFrame(body["data"])
    conn = _get_conn()
    df.to_sql("speed_cap_lookup", conn, if_exists="replace", index=False)
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/admin/upload", methods=["POST"])
def api_admin_upload():
    if request.form.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "No file uploaded"}), 400
    try:
        df = pd.read_csv(io.BytesIO(f.read()), encoding="utf-8-sig")
    except Exception as e:
        return jsonify({"error": f"Failed to read CSV: {e}"}), 400
    required_cols = {"State", "ATYPE", "FUNCL", "FTYPE", "POSTEDSP",
                     "Speed", "HourlyCapacity", "Alpha", "Beta",
                     "AM_CAP", "MD_CAP", "PM_CAP", "NT_CAP", "Daily_CAP"}
    missing = required_cols - set(df.columns)
    if missing:
        return jsonify({"error": f"Missing columns: {', '.join(sorted(missing))}"}), 400
    conn = _get_conn()
    df.to_sql("speed_cap_lookup", conn, if_exists="replace", index=False)
    conn.close()
    return jsonify({"ok": True, "rows": len(df)})


@app.route("/api/admin/reset", methods=["POST"])
def api_admin_reset():
    body = request.get_json()
    if body.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    conn = _get_conn()
    original = pd.read_sql("SELECT * FROM speed_cap_lookup_original", conn)
    original.to_sql("speed_cap_lookup", conn, if_exists="replace", index=False)
    conn.close()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
