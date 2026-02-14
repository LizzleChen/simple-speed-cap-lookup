import streamlit as st
import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent
LOOKUP_PATH = DATA_DIR / "speed_cap_lookup.csv"
FCFT_PATH = DATA_DIR / "fc_ft.csv"

ATYPE_LABELS = {1: "CBD", 2: "CBD Fringe", 3: "Urban", 4: "Suburban", 5: "Rural"}

PERIOD_HOURS = {"AM": 2, "Midday": 6, "PM": 4, "Night": 12, "Daily": 24}

# Special FUNCL=0 entries not in fc_ft.csv
SPECIAL_FTYPES = {
    30: "Walk access connector",
    0: "Centroid connector",
}

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data
def load_lookup() -> pd.DataFrame:
    df = pd.read_csv(LOOKUP_PATH, encoding="utf-8-sig")
    # Ensure numeric types
    for col in ["ATYPE", "FUNCL", "FTYPE", "POSTEDSP", "Speed", "HourlyCapacity"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data
def load_fcft() -> pd.DataFrame:
    return pd.read_csv(FCFT_PATH, encoding="utf-8-sig")


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

    # ---- Build roadway type options ----
    # From fc_ft.csv
    roadway_options: dict[str, tuple[int, int]] = {}
    for _, row in fcft.iterrows():
        label = f"{row['Roadway']}  (FUNCL={int(row['FNCL'])}, FTYPE={int(row['FTYPE'])})"
        roadway_options[label] = (int(row["FNCL"]), int(row["FTYPE"]))

    # Add special FUNCL=0 types
    for ftype, desc in SPECIAL_FTYPES.items():
        label = f"{desc}  (FUNCL=0, FTYPE={ftype})"
        roadway_options[label] = (0, ftype)

    # ---- Dropdown 1: Roadway Type ----
    selected_label = st.selectbox("Roadway Type", list(roadway_options.keys()))
    funcl, ftype = roadway_options[selected_label]

    # Filter data to selected roadway
    filtered = working[(working["FUNCL"] == funcl) & (working["FTYPE"] == ftype)]

    if filtered.empty:
        st.warning("No data available for this roadway type.")
        st.stop()

    # ---- Dropdown 2: Area Type ----
    available_atypes = sorted(filtered["ATYPE"].dropna().unique())
    atype_display = {a: f"{int(a)} - {ATYPE_LABELS.get(int(a), 'Unknown')}" for a in available_atypes}
    selected_atype_label = st.selectbox("Area Type", list(atype_display.values()))
    selected_atype = available_atypes[list(atype_display.values()).index(selected_atype_label)]

    filtered = filtered[filtered["ATYPE"] == selected_atype]

    # ---- Dropdown 3: Posted Speed (skip if not applicable) ----
    available_speeds = sorted(filtered["POSTEDSP"].dropna().unique())

    if len(available_speeds) > 0:
        speed_labels = [str(int(s)) for s in available_speeds]
        selected_speed_label = st.selectbox("Posted Speed", speed_labels)
        selected_speed = available_speeds[speed_labels.index(selected_speed_label)]
        result = filtered[filtered["POSTEDSP"] == selected_speed]
    else:
        st.info("Posted speed is not applicable for this roadway type.")
        result = filtered

    if result.empty:
        st.warning("No matching record found.")
        st.stop()

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
        use_container_width=True,
        hide_index=True,
    )

# ===========================================================================
# Page 2: Table Management
# ===========================================================================
elif page == "Table Management":
    st.title("Table Management")

    tab_edit, tab_upload = st.tabs(["View & Edit", "Upload CSV"])

    # ---- Tab 1: View & Edit ----
    with tab_edit:
        st.subheader("Speed & Capacity Lookup Table")

        lookup = load_lookup()

        if "edited_lookup" not in st.session_state:
            st.session_state.edited_lookup = None

        edited = st.data_editor(lookup, num_rows="dynamic", use_container_width=True, key="lookup_editor")

        col_save, col_discard = st.columns(2)
        with col_save:
            if st.button("Save Changes", type="primary"):
                edited.to_csv(LOOKUP_PATH, index=False, encoding="utf-8-sig")
                load_lookup.clear()
                st.success("Lookup table saved.")
                st.rerun()
        with col_discard:
            if st.button("Discard Changes"):
                st.rerun()

        with st.expander("Functional Class / Facility Type Reference (read-only)"):
            st.dataframe(load_fcft(), use_container_width=True, hide_index=True)

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
                st.dataframe(new_df.head(20), use_container_width=True, hide_index=True)
                st.caption(f"{len(new_df)} rows detected.")
                if st.button("Confirm & Replace", type="primary"):
                    new_df.to_csv(LOOKUP_PATH, index=False, encoding="utf-8-sig")
                    load_lookup.clear()
                    st.success("Lookup table replaced successfully.")
                    st.rerun()
