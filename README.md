# Speed & Capacity Lookup

A Streamlit web application for looking up roadway speed and capacity parameters used in transportation planning models.

## Overview

This tool allows users to query speed and hourly capacity values based on a combination of:

- **Functional Class (FUNCL)** — highway classification (e.g., IH freeway, arterial, collector)
- **Facility Type (FTYPE)** — specific roadway configuration (e.g., mainlanes only, with frontage roads)
- **Area Type (ATYPE)** — surrounding land use context (CBD, Urban, Suburban, Rural, etc.)
- **Posted Speed** — speed limit on the roadway

Results include the modeled **speed**, **hourly capacity**, and BPR curve parameters (**Alpha** and **Beta**). A built-in calculator shows period-based capacities (AM, Midday, PM, Night, Daily) adjusted by the number of lanes.

## Data Storage

Data is stored in a SQLite database (`data.db`) with the following tables:

| Table | Description |
|---|---|
| `speed_cap_lookup` | Main lookup table with speed, capacity, and BPR parameters by State/ATYPE/FUNCL/FTYPE/POSTEDSP |
| `speed_cap_lookup_original` | Snapshot of the original lookup data, used for the reset feature |
| `fc_ft` | Reference table mapping Functional Class and Facility Type codes to roadway descriptions |

To initialize the database from CSV files, run the one-time migration script:

```bash
python migrate_to_sqlite.py
```

## Pages

- **Capacity Lookup** — cascading dropdowns to filter and display speed/capacity results
- **Table Management** (password-protected) — view, edit, upload replacement CSV data, or reset the lookup table to its original state

## Setup

```bash
pip install -r requirements.txt
python migrate_to_sqlite.py
streamlit run app.py
```

## Configuration

The admin password for the Table Management page defaults to `admin`. To change it, create `.streamlit/secrets.toml`:

```toml
admin_password = "your_password"
```

## Requirements

- Python 3.10+
- streamlit >= 1.32.0
- pandas >= 2.0.0
