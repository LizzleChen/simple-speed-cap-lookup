# Speed & Capacity Lookup

A web application for looking up roadway speed and capacity parameters used in transportation planning models. Available as both a **Flask** app and a **Streamlit** app.

## Overview

This tool allows users to query speed and hourly capacity values based on a combination of:

- **Functional Class (FUNCL)** — highway classification (e.g., IH freeway, arterial, collector)
- **Facility Type (FTYPE)** — specific roadway configuration (e.g., mainlanes only, with frontage roads)
- **Area Type (ATYPE)** — surrounding land use context (CBD, Urban, Suburban, Rural, etc.)
- **Posted Speed** — speed limit on the roadway

Results include the modeled **speed**, **hourly capacity**, and BPR curve parameters (**Alpha** and **Beta**). A built-in calculator shows period-based capacities (AM, Midday, PM, Night, Daily) adjusted by the number of lanes.

## Project Structure

```
simple-speed-cap-lookup/
├── flask/                  # Flask app (lightweight, faster on Windows)
│   ├── app.py
│   ├── requirements.txt
│   └── templates/
│       ├── lookup.html
│       └── admin.html
├── streamlit/              # Streamlit app (original)
│   ├── app.py
│   ├── requirements.txt
│   └── migrate_to_sqlite.py
├── data.db                 # Shared SQLite database
├── fc_ft.csv
├── speed_cap_lookup.csv
└── speed_cap_lookup_original.csv
```

## Data Storage

Data is stored in a SQLite database (`data.db`) in the project root, shared by both apps. Tables:

| Table | Description |
|---|---|
| `speed_cap_lookup` | Main lookup table with speed, capacity, and BPR parameters by State/ATYPE/FUNCL/FTYPE/POSTEDSP |
| `speed_cap_lookup_original` | Snapshot of the original lookup data, used for the reset feature |
| `fc_ft` | Reference table mapping Functional Class and Facility Type codes to roadway descriptions |

To initialize the database from CSV files, run the one-time migration script:

```bash
cd streamlit
python migrate_to_sqlite.py
```

## Pages

- **Capacity Lookup** — cascading dropdowns to filter and display speed/capacity results
- **Admin / Table Management** (password-protected) — view, edit, upload replacement CSV data, or reset the lookup table to its original state

## Setup

### Flask (recommended)

```bash
cd flask
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000

### Streamlit

```bash
cd streamlit
pip install -r requirements.txt
python migrate_to_sqlite.py   # first time only
streamlit run app.py
```

## Configuration

### Flask

Set the admin password via environment variable or `.env` file in the `flask/` directory:

```
ADMIN_PASSWORD=your_password
```

Defaults to `changeme` if not set.

### Streamlit

Create `streamlit/.streamlit/secrets.toml`:

```toml
admin_password = "your_password"
```

Defaults to `admin` if not set.

## Requirements

- Python 3.10+
- **Flask app:** flask, pandas, python-dotenv
- **Streamlit app:** streamlit >= 1.32.0, pandas >= 2.0.0
