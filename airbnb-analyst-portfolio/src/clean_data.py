"""Clean the raw Kaggle listings export and add a few derived columns.

Input:  data/raw/listings_raw.csv
Output: data/processed/listings_clean.csv
"""

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "listings_raw.csv"
OUT_PATH = ROOT / "data" / "processed" / "listings_clean.csv"

# a listing that's rarely blocked off AND belongs to a host running multiple
# listings looks more like a managed rental than someone's spare room
COMMERCIAL_AVAILABILITY_THRESHOLD = 270
COMMERCIAL_MIN_HOST_LISTINGS = 2


def load_raw() -> pd.DataFrame:
    return pd.read_csv(RAW_PATH)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # neighbourhood_group and license are 100% empty in this export, no point keeping them
    fully_null_cols = [c for c in df.columns if df[c].isna().all()]
    df = df.drop(columns=fully_null_cols)

    df["last_review"] = pd.to_datetime(df["last_review"], errors="coerce")

    # no reviews yet means 0/month, not "unknown" - leaving it NaN would break every average
    df["reviews_per_month"] = df["reviews_per_month"].fillna(0.0)
    df["name"] = df["name"].fillna("(no title provided)")
    df["host_name"] = df["host_name"].fillna("(unknown host)")

    # price is heavily skewed - a handful of £5k/night listings would wreck any mean,
    # so flag rather than delete, and keep a capped column for chart axes
    p99 = df["price"].quantile(0.99)
    df["is_zero_price"] = df["price"] == 0          # £0/night is a listing error, not a real rate
    df["is_price_outlier"] = (df["price"] == 0) | (df["price"] > p99)
    df["price_capped"] = df["price"].clip(upper=p99)

    df["has_reviews"] = df["number_of_reviews"] > 0
    df["days_since_last_review"] = (pd.Timestamp("2022-10-01") - df["last_review"]).dt.days

    bins = [0, 1, 2, 5, np.inf]
    labels = ["Single listing", "2 listings", "3-5 listings", "6+ listings (professional)"]
    df["host_tier"] = pd.cut(df["calculated_host_listings_count"], bins=bins, labels=labels)

    df["likely_commercial"] = (
        (df["room_type"] == "Entire home/apt")
        & (df["calculated_host_listings_count"] >= COMMERCIAL_MIN_HOST_LISTINGS)
        & (df["availability_365"] >= COMMERCIAL_AVAILABILITY_THRESHOLD)
    )

    availability_bins = [-1, 0, 90, 180, 270, 366]
    availability_labels = ["Never available", "Low (1-90d)", "Moderate (91-180d)",
                            "High (181-270d)", "Very high (271-365d)"]
    df["availability_tier"] = pd.cut(df["availability_365"], bins=availability_bins, labels=availability_labels)

    return df


def print_data_quality_summary(raw: pd.DataFrame, clean_df: pd.DataFrame):
    print("=" * 70)
    print("DATA QUALITY SUMMARY")
    print("=" * 70)
    print(f"Raw rows: {len(raw):,}  |  Clean rows: {len(clean_df):,}")
    fully_null = [c for c in raw.columns if raw[c].isna().all()]
    print(f"Fully-null columns dropped: {fully_null}")
    print(f"Zero-price listings flagged: {int(clean_df['is_zero_price'].sum())}")
    print(f"Price outliers flagged (>{raw['price'].quantile(0.99):.0f}, 99th pct): "
          f"{int(clean_df['is_price_outlier'].sum())}")
    print(f"Listings with no reviews yet: {int((~clean_df['has_reviews']).sum())} "
          f"({(~clean_df['has_reviews']).mean()*100:.1f}%)")
    print(f"Listings flagged 'likely_commercial': {int(clean_df['likely_commercial'].sum())} "
          f"({clean_df['likely_commercial'].mean()*100:.1f}%)")
    print(f"Unique hosts: {clean_df['host_id'].nunique():,}  |  Unique listings: {len(clean_df):,}")


def main():
    raw = load_raw()
    clean_df = clean(raw)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(OUT_PATH, index=False)
    print_data_quality_summary(raw, clean_df)
    print(f"\nCleaned dataset written to: {OUT_PATH}")


if __name__ == "__main__":
    main()
