"""Load listings from the database, compute the summary tables, save all
the report charts to outputs/figures. Run with: python3 src/analysis.py"""

import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import seaborn as sns

from metrics import (
    robust_price_stats,
    host_concentration_index,
    commercial_listing_summary,
    demand_supply_view,
)

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "database" / "airbnb.db"
FIG_DIR = ROOT / "outputs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", context="talk")


def load_listings() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM listings", conn, parse_dates=["last_review"])
    conn.close()
    return df


def chart_price_by_borough(df: pd.DataFrame, top_n: int = 15):
    stats = robust_price_stats(df, "neighbourhood").head(top_n)
    fig, ax = plt.subplots(figsize=(11, 7))
    sns.barplot(data=stats, y="neighbourhood", x="median_price", hue="neighbourhood",
                palette="viridis", legend=False, ax=ax)
    ax.set_title(f"Median Nightly Price by Borough (Top {top_n} of 33)")
    ax.set_xlabel("Median Price (£)")
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "01_median_price_by_borough.png", dpi=150)
    plt.close(fig)


def chart_price_by_room_type(df: pd.DataFrame):
    clean = df[df["is_price_outlier"] == 0]
    fig, ax = plt.subplots(figsize=(9, 6))
    order = clean.groupby("room_type")["price"].median().sort_values(ascending=False).index
    sns.boxplot(data=clean, x="room_type", y="price", order=order, hue="room_type",
                palette="mako", legend=False, ax=ax, showfliers=False)
    ax.set_title("Price Distribution by Room Type (outliers excluded)")
    ax.set_xlabel("")
    ax.set_ylabel("Price (£/night)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "02_price_by_room_type.png", dpi=150)
    plt.close(fig)


def chart_geographic_scatter(df: pd.DataFrame):
    # plotting raw lat/lon with no basemap still traces London's outline clearly
    clean = df[df["is_price_outlier"] == 0]
    fig, ax = plt.subplots(figsize=(9, 8))
    sc = ax.scatter(clean["longitude"], clean["latitude"], c=clean["price"],
                     cmap="plasma", s=4, alpha=0.5)
    cbar = fig.colorbar(sc, ax=ax)
    cbar.set_label("Price (£/night)")
    ax.set_title("London Airbnb Listings by Location and Price")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "03_geographic_price_map.png", dpi=150)
    plt.close(fig)


def chart_host_tier_composition(df: pd.DataFrame):
    tier_counts = df["host_tier"].value_counts()
    tier_avg_price = df[df["is_price_outlier"] == 0].groupby("host_tier")["price"].mean()

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    order = ["Single listing", "2 listings", "3-5 listings", "6+ listings (professional)"]
    tier_counts = tier_counts.reindex(order)
    axes[0].pie(tier_counts, labels=tier_counts.index, autopct="%1.1f%%",
                colors=sns.color_palette("viridis", 4), startangle=90)
    axes[0].set_title("Share of Listings by Host Tier")

    tier_avg_price = tier_avg_price.reindex(order)
    sns.barplot(x=tier_avg_price.index, y=tier_avg_price.values, hue=tier_avg_price.index,
                palette="mako", legend=False, ax=axes[1])
    axes[1].set_title("Average Price by Host Tier")
    axes[1].set_ylabel("Avg. Price (£/night)")
    axes[1].set_xlabel("")
    axes[1].tick_params(axis="x", rotation=25)

    fig.tight_layout()
    fig.savefig(FIG_DIR / "04_host_tier_composition.png", dpi=150)
    plt.close(fig)


def chart_commercial_by_borough(df: pd.DataFrame, top_n: int = 15):
    summary = commercial_listing_summary(df).head(top_n)
    fig, ax = plt.subplots(figsize=(11, 7))
    sns.barplot(data=summary, y="neighbourhood", x="pct_commercial", hue="neighbourhood",
                palette="rocket", legend=False, ax=ax)
    ax.set_title(f"Likely-Commercial Listing Share by Borough (Top {top_n})")
    ax.set_xlabel("% of Listings Flagged 'Likely Commercial'")
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "05_commercial_share_by_borough.png", dpi=150)
    plt.close(fig)


def chart_minimum_nights_distribution(df: pd.DataFrame):
    bins = [0, 1, 3, 7, 29, 90, df["minimum_nights"].max() + 1]
    labels = ["1 night", "2-3 nights", "4-7 nights", "8-29 nights", "30-89 nights", "90+ nights"]
    df = df.copy()
    df["min_nights_bucket"] = pd.cut(df["minimum_nights"], bins=bins, labels=labels, right=True)
    counts = df["min_nights_bucket"].value_counts().reindex(labels)

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(x=counts.index, y=counts.values, hue=counts.index, palette="crest",
                legend=False, ax=ax)
    ax.set_title("Minimum-Nights Requirement Distribution")
    ax.set_ylabel("Number of Listings")
    ax.set_xlabel("")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "06_minimum_nights_distribution.png", dpi=150)
    plt.close(fig)


def chart_demand_vs_price(df: pd.DataFrame):
    summary = demand_supply_view(df)
    fig, ax = plt.subplots(figsize=(9, 7))
    sc = ax.scatter(summary["avg_price"], summary["avg_reviews_per_month"],
                     s=summary["n_listings"] / 15, alpha=0.7, c=summary["n_listings"],
                     cmap="viridis", edgecolor="black")
    for _, row in summary.iterrows():
        # only label the boroughs worth calling out, otherwise 33 labels overlap into noise
        if row["n_listings"] > 1000 or row["avg_reviews_per_month"] > 0.85:
            ax.annotate(row["neighbourhood"], (row["avg_price"], row["avg_reviews_per_month"]),
                        xytext=(5, 5), textcoords="offset points", fontsize=9)
    cbar = fig.colorbar(sc, ax=ax)
    cbar.set_label("Number of Listings")
    ax.set_xlabel("Average Price (£/night)")
    ax.set_ylabel("Average Reviews per Month (demand proxy)")
    ax.set_title("Demand vs. Price by Borough (bubble size = supply)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "07_demand_vs_price.png", dpi=150)
    plt.close(fig)


def main():
    df = load_listings()

    price_stats = robust_price_stats(df, "neighbourhood")
    price_stats.to_csv(ROOT / "outputs" / "price_stats_by_borough.csv", index=False)

    concentration = host_concentration_index(df)
    pd.DataFrame([concentration]).to_csv(ROOT / "outputs" / "host_concentration.csv", index=False)

    commercial = commercial_listing_summary(df)
    commercial.to_csv(ROOT / "outputs" / "commercial_listings_by_borough.csv", index=False)

    demand = demand_supply_view(df)
    demand.to_csv(ROOT / "outputs" / "demand_supply_by_borough.csv", index=False)

    chart_price_by_borough(df)
    chart_price_by_room_type(df)
    chart_geographic_scatter(df)
    chart_host_tier_composition(df)
    chart_commercial_by_borough(df)
    chart_minimum_nights_distribution(df)
    chart_demand_vs_price(df)

    print("=" * 70)
    print("HOST CONCENTRATION")
    print("=" * 70)
    for k, v in concentration.items():
        print(f"{k}: {v}")

    print("\n" + "=" * 70)
    print("TOP 10 BOROUGHS BY MEDIAN PRICE")
    print("=" * 70)
    print(price_stats.head(10).to_string(index=False))

    print("\n" + "=" * 70)
    print("TOP 10 BOROUGHS BY LIKELY-COMMERCIAL SHARE")
    print("=" * 70)
    print(commercial.head(10).to_string(index=False))

    print("\nCharts saved to:", FIG_DIR)


if __name__ == "__main__":
    main()
