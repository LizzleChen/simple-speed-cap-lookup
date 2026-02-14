# Speed & Capacity Lookup

A Streamlit web application for looking up roadway speed and capacity parameters used in transportation planning models.

## Overview

This tool allows users to query speed and hourly capacity values based on a combination of:

- **Functional Class (FUNCL)** — highway classification (e.g., IH freeway, arterial, collector)
- **Facility Type (FTYPE)** — specific roadway configuration (e.g., mainlanes only, with frontage roads)
- **Area Type (ATYPE)** — surrounding land use context (CBD, Urban, Suburban, Rural, etc.)
- **Posted Speed** — speed limit on the roadway

Results include the modeled **speed**, **hourly capacity**, and BPR curve parameters (**Alpha** and **Beta**). A built-in calculator shows period-based capacities (AM, Midday, PM, Night, Daily) adjusted by the number of lanes.

## Data Files

| File | Description |
|---|---|
| `speed_cap_lookup.csv` | Main lookup table with speed, capacity, and BPR parameters by State/ATYPE/FUNCL/FTYPE/POSTEDSP |
| `fc_ft.csv` | Reference table mapping Functional Class and Facility Type codes to roadway descriptions |

## Pages

- **Capacity Lookup** — cascading dropdowns to filter and display speed/capacity results
- **Table Management** — view, edit, and upload replacement CSV data for the lookup table

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Requirements

- Python 3.10+
- streamlit >= 1.32.0
- pandas >= 2.0.0
