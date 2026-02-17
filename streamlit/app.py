import sqlite3
import streamlit as st
import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent.parent
DB_PATH = DATA_DIR / "data.db"

ADMIN_PASSWORD = st.secrets.get("admin_password", "admin")

ATYPE_LABELS = {1: "CBD", 2: "CBD Fringe", 3: "Urban", 4: "Suburban", 5: "Rural"}

PERIOD_HOURS = {"AM": 2, "Midday": 6, "PM": 4, "Night": 12, "Daily": 24}

# Special FUNCL=0 entries not in fc_ft
SPECIAL_FTYPES = {
    30: "Walk access connector",
    0: "Centroid connector",
}

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _get_conn():
    return sqlite3.connect(DB_PATH)


@st.cache_data
def load_lookup() -> pd.DataFrame:
    conn = _get_conn()
    df = pd.read_sql("SELECT * FROM speed_cap_lookup", conn)
    conn.close()
    for col in ["ATYPE", "FUNCL", "FTYPE", "POSTEDSP", "Speed", "HourlyCapacity"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data
def load_fcft() -> pd.DataFrame:
    conn = _get_conn()
    df = pd.read_sql("SELECT * FROM fc_ft", conn)
    conn.close()
    return df


def save_lookup(df: pd.DataFrame):
    conn = _get_conn()
    df.to_sql("speed_cap_lookup", conn, if_exists="replace", index=False)
    conn.close()
    load_lookup.clear()


def reset_lookup():
    conn = _get_conn()
    original = pd.read_sql("SELECT * FROM speed_cap_lookup_original", conn)
    original.to_sql("speed_cap_lookup", conn, if_exists="replace", index=False)
    conn.close()
    load_lookup.clear()


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Speed & Capacity Lookup", layout="wide")

page = st.sidebar.radio("Navigate", ["Capacity Lookup", "Table Management"])

# ===========================================================================
# Page 1: Capacity Lookup
# ===========================================================================
if page == "Capacity Lookup":
    st.title("Speed & Capacity Lookup")

    lookup = load_lookup()
    fcft = load_fcft()

    # Default to TX rows; use All rows as fallback for centroid connectors
    tx = lookup[lookup["State"] == "TX"]
    all_rows = lookup[lookup["State"] == "All"]
    working = pd.concat([tx, all_rows]).drop_duplicates()

    # ---- Build FUNCL and FTYPE options from fc_ft ----
    # Map FUNCL -> list of (FTYPE, Roadway name)
    funcl_to_ftypes: dict[int, list[tuple[int, str]]] = {}
    for _, row in fcft.iterrows():
        fc = int(row["FNCL"])
        ft = int(row["FTYPE"])
        name = row["Roadway"]
        funcl_to_ftypes.setdefault(fc, []).append((ft, name))

    # Add special FUNCL=0 types
    for ft, desc in SPECIAL_FTYPES.items():
        funcl_to_ftypes.setdefault(0, []).append((ft, desc))

    # All FUNCL values sorted
    all_funcls = sorted(funcl_to_ftypes.keys())

    # ---- Dropdown 1: Functional Class (FUNCL) ----
    selected_funcl = st.selectbox(
        "Functional Class (FUNCL)",
        all_funcls,
        index=None,
        placeholder="Select a functional class...",
    )

    # ---- Dropdown 2: Facility Type (FTYPE) ----
    # Show all FTYPEs if no FUNCL selected, otherwise filter to selected FUNCL
    if selected_funcl is not None:
        ftype_entries = sorted(funcl_to_ftypes[selected_funcl], key=lambda x: x[0])
    else:
        ftype_entries = sorted(
            [(ft, name) for entries in funcl_to_ftypes.values() for ft, name in entries],
            key=lambda x: x[0],
        )
    ftype_labels = [f"{ft} - {name}" for ft, name in ftype_entries]

    selected_ftype_label = st.selectbox(
        "Facility Type (FTYPE)",
        ftype_labels,
        index=None,
        placeholder="Select a facility type...",
    )

    # ---- Dropdown 3: Area Type ----
    # Build available area types based on current filters
    if selected_ftype_label is not None:
        ftype = ftype_entries[ftype_labels.index(selected_ftype_label)][0]
        filtered = working[working["FTYPE"] == ftype]
        if selected_funcl is not None:
            filtered = filtered[filtered["FUNCL"] == selected_funcl]
        available_atypes = sorted(filtered["ATYPE"].dropna().unique())
    else:
        filtered = working
        available_atypes = sorted(working["ATYPE"].dropna().unique())

    atype_display = [f"{int(a)} - {ATYPE_LABELS.get(int(a), 'Unknown')}" for a in available_atypes]
    selected_atype_label = st.selectbox(
        "Area Type",
        atype_display,
        index=None,
        placeholder="Select an area type...",
    )

    # ---- Dropdown 4: Posted Speed ----
    # Build available speeds based on current filters
    if selected_ftype_label is not None and selected_atype_label is not None:
        selected_atype = available_atypes[atype_display.index(selected_atype_label)]
        filtered = filtered[filtered["ATYPE"] == selected_atype]
        available_speeds = sorted(filtered["POSTEDSP"].dropna().unique())
    else:
        available_speeds = sorted(working["POSTEDSP"].dropna().unique())

    if len(available_speeds) > 0:
        speed_labels = [str(int(s)) for s in available_speeds]
        selected_speed_label = st.selectbox(
            "Posted Speed",
            speed_labels,
            index=None,
            placeholder="Select a posted speed...",
        )
    else:
        selected_speed_label = None
        if selected_ftype_label is not None:
            st.info("Posted speed is not applicable for this roadway type.")

    # ---- Show results only when all required selections are made ----
    all_selected = (
        selected_ftype_label is not None
        and selected_atype_label is not None
        and (selected_speed_label is not None or len(available_speeds) == 0)
    )

    if all_selected:
        if len(available_speeds) > 0:
            selected_speed = available_speeds[speed_labels.index(selected_speed_label)]
            result = filtered[filtered["POSTEDSP"] == selected_speed]
        else:
            result = filtered

        if result.empty:
            st.warning("No matching record found.")
        else:
            row = result.iloc[0]

            # ---- Display result metrics ----
            st.divider()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Speed", int(row["Speed"]))
            c2.metric("Hourly Capacity", f"{int(row['HourlyCapacity']):,}")
            c3.metric("Alpha", row["Alpha"])
            c4.metric("Beta", row["Beta"])

            # ---- Number of lanes ----
            lanes = st.number_input("Number of Lanes", min_value=1, value=1, step=1)

            hourly_cap = int(row["HourlyCapacity"])

            # ---- Period capacity table ----
            table_data = []
            for period, hours in PERIOD_HOURS.items():
                base = hourly_cap * hours
                adjusted = base * lanes
                table_data.append({
                    "Period": period,
                    "Hours": hours,
                    "Base Capacity (per lane)": f"{base:,}",
                    "Adjusted Capacity (× lanes)": f"{adjusted:,}",
                })

            st.dataframe(
                pd.DataFrame(table_data),
                width='content',
                hide_index=True,
            )

# ===========================================================================
# Page 2: Table Management (password-protected)
# ===========================================================================
elif page == "Table Management":
    st.title("Table Management")

    password = st.text_input("Admin Password", type="password")
    if password != ADMIN_PASSWORD:
        if password:
            st.error("Incorrect password.")
        st.stop()

    tab_edit, tab_upload, tab_reset = st.tabs(["View & Edit", "Upload CSV", "Reset"])

    # ---- Tab 1: View & Edit ----
    with tab_edit:
        st.subheader("Speed & Capacity Lookup Table")

        lookup = load_lookup()

        edited = st.data_editor(lookup, num_rows="dynamic", width='content', key="lookup_editor")

        col_save, col_discard = st.columns(2)
        with col_save:
            if st.button("Save Changes", type="primary"):
                save_lookup(edited)
                st.success("Lookup table saved.")
                st.rerun()
        with col_discard:
            if st.button("Discard Changes"):
                st.rerun()

        with st.expander("Functional Class / Facility Type Reference (read-only)"):
            st.dataframe(load_fcft(), width='content', hide_index=True)

    # ---- Tab 2: Upload CSV ----
    with tab_upload:
        st.subheader("Replace Lookup Table via CSV Upload")

        uploaded = st.file_uploader("Upload a CSV file", type=["csv"])
        if uploaded is not None:
            try:
                new_df = pd.read_csv(uploaded, encoding="utf-8-sig")
            except Exception as e:
                st.error(f"Failed to read CSV: {e}")
                st.stop()

            required_cols = {"State", "ATYPE", "FUNCL", "FTYPE", "POSTEDSP",
                             "Speed", "HourlyCapacity", "Alpha", "Beta",
                             "AM_CAP", "MD_CAP", "PM_CAP", "NT_CAP", "Daily_CAP"}
            missing = required_cols - set(new_df.columns)
            if missing:
                st.error(f"Missing required columns: {', '.join(sorted(missing))}")
            else:
                st.dataframe(new_df.head(20), width='content', hide_index=True)
                st.caption(f"{len(new_df)} rows detected.")
                if st.button("Confirm & Replace", type="primary"):
                    save_lookup(new_df)
                    st.success("Lookup table replaced successfully.")
                    st.rerun()

    # ---- Tab 3: Reset to Original ----
    with tab_reset:
        st.subheader("Reset to Original Data")
        st.warning("This will discard all edits and restore the lookup table to its original state.")
        if st.button("Reset to Original", type="primary"):
            reset_lookup()
            st.success("Lookup table has been reset to original data.")
            st.rerun()
