"""One-time migration: load CSVs into a SQLite database."""

import sqlite3
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent
DB_PATH = DATA_DIR / "data.db"
LOOKUP_CSV = DATA_DIR / "speed_cap_lookup.csv"
FCFT_CSV = DATA_DIR / "fc_ft.csv"
ORIGINAL_CSV = DATA_DIR / "speed_cap_lookup_original.csv"


def migrate():
    conn = sqlite3.connect(DB_PATH)

    # Speed cap lookup table
    lookup = pd.read_csv(LOOKUP_CSV, encoding="utf-8-sig")
    lookup.to_sql("speed_cap_lookup", conn, if_exists="replace", index=False)
    print(f"speed_cap_lookup: {len(lookup)} rows")

    # FC/FT reference table
    fcft = pd.read_csv(FCFT_CSV, encoding="utf-8-sig")
    fcft.to_sql("fc_ft", conn, if_exists="replace", index=False)
    print(f"fc_ft: {len(fcft)} rows")

    # Store the original lookup CSV for reset functionality
    if ORIGINAL_CSV.exists():
        original = pd.read_csv(ORIGINAL_CSV, encoding="utf-8-sig")
    else:
        original = lookup.copy()
    original.to_sql("speed_cap_lookup_original", conn, if_exists="replace", index=False)
    print(f"speed_cap_lookup_original (for reset): {len(original)} rows")

    conn.close()
    print(f"\nDatabase created at: {DB_PATH}")


if __name__ == "__main__":
    migrate()
