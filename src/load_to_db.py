"""Load the cleaned CSV into SQLite and roll up a hosts table from it."""

import sqlite3
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN_PATH = ROOT / "data" / "processed" / "listings_clean.csv"
DB_PATH = ROOT / "data" / "database" / "airbnb.db"
SCHEMA_PATH = ROOT / "sql" / "schema.sql"

LISTINGS_COLUMNS = [
    "id", "name", "host_id", "host_name", "neighbourhood", "latitude", "longitude",
    "room_type", "price", "price_capped", "is_zero_price", "is_price_outlier",
    "minimum_nights", "number_of_reviews", "last_review", "reviews_per_month",
    "calculated_host_listings_count", "availability_365", "availability_tier",
    "number_of_reviews_ltm", "has_reviews", "days_since_last_review", "host_tier",
    "likely_commercial",
]


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())

    df = pd.read_csv(CLEAN_PATH)

    listings_df = df[LISTINGS_COLUMNS].copy()
    # sqlite has no real boolean type, store these as 0/1
    for bool_col in ["is_zero_price", "is_price_outlier", "has_reviews", "likely_commercial"]:
        listings_df[bool_col] = listings_df[bool_col].astype(int)
    listings_df.to_sql("listings", conn, if_exists="append", index=False)
    print(f"Loaded {len(listings_df):>6,} rows into 'listings'")

    # one row per host, so we can join listings -> hosts like a real schema instead of one flat table
    hosts_df = (
        df.groupby("host_id")
        .agg(
            host_name=("host_name", "first"),
            total_listings=("id", "count"),
            total_reviews=("number_of_reviews", "sum"),
            avg_price=("price", "mean"),
            boroughs_active_in=("neighbourhood", "nunique"),
            host_tier=("host_tier", "first"),
        )
        .reset_index()
    )
    hosts_df["avg_price"] = hosts_df["avg_price"].round(2)
    hosts_df.to_sql("hosts", conn, if_exists="append", index=False)
    print(f"Loaded {len(hosts_df):>6,} rows into 'hosts'")

    conn.commit()
    conn.close()
    print(f"\nDatabase ready at: {DB_PATH}")


if __name__ == "__main__":
    main()
