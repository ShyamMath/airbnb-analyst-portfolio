"""Pricing, host-concentration, and demand calculations used by both the
notebook and the dashboard, so the numbers never drift out of sync."""

import numpy as np
import pandas as pd


def robust_price_stats(df: pd.DataFrame, group_col: str = None) -> pd.DataFrame:
    """Median/IQR price stats, optionally grouped. Price is right-skewed so
    median (not mean) is what we report as the headline number."""
    clean = df[df["is_price_outlier"] == 0]
    grouped = clean.groupby(group_col) if group_col else [(None, clean)]

    rows = []
    for key, g in grouped:
        rows.append({
            group_col or "group": key,
            "n_listings": len(g),
            "median_price": g["price"].median(),
            "mean_price": round(g["price"].mean(), 2),
            "p25_price": g["price"].quantile(0.25),
            "p75_price": g["price"].quantile(0.75),
            "std_price": round(g["price"].std(), 2),
        })
    result = pd.DataFrame(rows)
    if group_col:
        result = result.sort_values("median_price", ascending=False).reset_index(drop=True)
    return result


def host_concentration_index(df: pd.DataFrame) -> dict:
    """HHI (market-concentration metric from antitrust analysis) applied to
    listing ownership per host. Low HHI here just means no single host
    dominates - it doesn't say anything about how big the multi-listing
    segment is overall, which is why we also return that share separately."""
    listings_per_host = df.groupby("host_id").size()
    total = listings_per_host.sum()
    shares = (listings_per_host / total) * 100
    hhi = (shares ** 2).sum()

    top_10_share = listings_per_host.sort_values(ascending=False).head(10).sum() / total * 100
    multi_listing_share = listings_per_host[listings_per_host > 1].sum() / total * 100

    return {
        "hhi": round(hhi, 2),
        "top_10_hosts_share_pct": round(top_10_share, 2),
        "multi_listing_host_share_pct": round(multi_listing_share, 2),
        "n_unique_hosts": int(listings_per_host.shape[0]),
        "n_listings": int(total),
    }


def commercial_listing_summary(df: pd.DataFrame, group_col: str = "neighbourhood") -> pd.DataFrame:
    """Share of listings flagged likely_commercial, by group."""
    summary = (
        df.groupby(group_col)
        .agg(total_listings=("id", "count"), commercial_listings=("likely_commercial", "sum"))
        .reset_index()
    )
    summary["pct_commercial"] = round(summary["commercial_listings"] / summary["total_listings"] * 100, 2)
    return summary.sort_values("pct_commercial", ascending=False).reset_index(drop=True)


def demand_supply_view(df: pd.DataFrame, group_col: str = "neighbourhood") -> pd.DataFrame:
    """Reviews/month as a stand-in for demand, since there's no real booking
    or occupancy data in this export - more completed stays roughly means
    more reviews, but it's a proxy, not a direct measurement."""
    clean = df[df["is_price_outlier"] == 0]
    summary = (
        clean.groupby(group_col)
        .agg(
            n_listings=("id", "count"),
            avg_reviews_per_month=("reviews_per_month", "mean"),
            avg_price=("price", "mean"),
            pct_with_reviews=("has_reviews", "mean"),
        )
        .reset_index()
    )
    summary["avg_reviews_per_month"] = summary["avg_reviews_per_month"].round(2)
    summary["avg_price"] = summary["avg_price"].round(2)
    summary["pct_with_reviews"] = (summary["pct_with_reviews"] * 100).round(1)
    return summary.sort_values("avg_reviews_per_month", ascending=False).reset_index(drop=True)


def price_percentile_within_group(df: pd.DataFrame, group_col: str = "neighbourhood") -> pd.Series:
    """Where a listing's price ranks (0-100) against others in its own borough."""
    clean = df[df["is_price_outlier"] == 0]
    return clean.groupby(group_col)["price"].rank(pct=True) * 100
