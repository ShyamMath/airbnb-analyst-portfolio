"""Run with: streamlit run dashboard/app.py"""

import sqlite3
from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from metrics import (  # noqa: E402
    robust_price_stats,
    host_concentration_index,
    commercial_listing_summary,
    demand_supply_view,
)

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "database" / "airbnb.db"

st.set_page_config(page_title="London Airbnb Research Dashboard", layout="wide")


@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM listings", conn, parse_dates=["last_review"])
    conn.close()
    return df


listings = load_data()

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
st.sidebar.title("🏠 Filters")

boroughs = sorted(listings["neighbourhood"].unique())
selected_boroughs = st.sidebar.multiselect("Borough", boroughs, default=boroughs)

room_types = sorted(listings["room_type"].unique())
selected_room_types = st.sidebar.multiselect("Room type", room_types, default=room_types)

price_max_default = int(listings[listings["is_price_outlier"] == 0]["price"].max())
price_range = st.sidebar.slider("Price range (£/night)", 0, price_max_default, (0, price_max_default))

exclude_outliers = st.sidebar.checkbox("Exclude flagged price outliers", value=True)

mask = (
    listings["neighbourhood"].isin(selected_boroughs)
    & listings["room_type"].isin(selected_room_types)
    & listings["price"].between(price_range[0], price_range[1])
)
if exclude_outliers:
    mask &= listings["is_price_outlier"] == 0

filtered = listings[mask]

st.sidebar.markdown("---")
st.sidebar.caption(
    f"Showing **{len(filtered):,}** of {len(listings):,} listings.  \n"
    "Source: Inside Airbnb London export (Kaggle). "
    "`likely_commercial` is a heuristic, not confirmed regulatory status — see README."
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("London Airbnb Market Research Dashboard")
st.caption("Interactive companion to `reports/research_report.md` and `notebooks/research_analysis.ipynb`")

if filtered.empty:
    st.warning("No listings match the current filters. Try widening your selection.")
    st.stop()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Listings shown", f"{len(filtered):,}")
col2.metric("Median price", f"£{filtered[filtered['is_price_outlier']==0]['price'].median():.0f}")
col3.metric("Unique hosts", f"{filtered['host_id'].nunique():,}")
col4.metric("% likely commercial", f"{filtered['likely_commercial'].mean()*100:.1f}%")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_map, tab_price, tab_hosts, tab_demand = st.tabs(
    ["🗺️ Map", "💷 Pricing", "🏢 Host Composition", "📈 Demand"]
)

with tab_map:
    # capping the sample keeps the map from lagging when all boroughs are selected
    map_df = filtered.sample(min(len(filtered), 8000), random_state=42)
    fig = px.scatter_mapbox(
        map_df, lat="latitude", lon="longitude", color="price",
        color_continuous_scale="Plasma", size_max=6, zoom=9,
        hover_name="name", hover_data={"neighbourhood": True, "room_type": True, "price": True,
                                        "latitude": False, "longitude": False},
        mapbox_style="open-street-map", height=650,
    )
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Showing a random sample of up to 8,000 filtered listings for map responsiveness.")

with tab_price:
    col1, col2 = st.columns(2)
    with col1:
        stats = robust_price_stats(filtered, "neighbourhood")
        fig2 = px.bar(stats.head(20), x="median_price", y="neighbourhood", orientation="h",
                       title="Median Price by Borough", color="median_price",
                       color_continuous_scale="Viridis")
        fig2.update_layout(height=550, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig2, use_container_width=True)
    with col2:
        clean = filtered[filtered["is_price_outlier"] == 0]
        fig3 = px.box(clean, x="room_type", y="price", color="room_type",
                       title="Price Distribution by Room Type", points=False)
        fig3.update_layout(height=550, showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)

    st.markdown("#### Price statistics by borough")
    st.dataframe(stats, hide_index=True, use_container_width=True)

with tab_hosts:
    concentration = host_concentration_index(filtered)
    col1, col2, col3 = st.columns(3)
    col1.metric("HHI (listing concentration)", concentration["hhi"])
    col2.metric("Top 10 hosts' share", f"{concentration['top_10_hosts_share_pct']}%")
    col3.metric("Multi-listing host share", f"{concentration['multi_listing_host_share_pct']}%")

    col1, col2 = st.columns(2)
    with col1:
        tier_order = ["Single listing", "2 listings", "3-5 listings", "6+ listings (professional)"]
        tier_counts = filtered["host_tier"].value_counts().reindex(tier_order).fillna(0)
        fig4 = px.pie(values=tier_counts.values, names=tier_counts.index,
                       title="Share of Listings by Host Tier", color_discrete_sequence=px.colors.sequential.Viridis)
        st.plotly_chart(fig4, use_container_width=True)
    with col2:
        commercial = commercial_listing_summary(filtered)
        fig5 = px.bar(commercial.head(15), x="pct_commercial", y="neighbourhood", orientation="h",
                       title="Likely-Commercial Listing Share by Borough", color="pct_commercial",
                       color_continuous_scale="Reds")
        fig5.update_layout(height=450, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig5, use_container_width=True)

with tab_demand:
    demand = demand_supply_view(filtered)
    fig6 = px.scatter(demand, x="avg_price", y="avg_reviews_per_month", size="n_listings",
                       color="n_listings", hover_name="neighbourhood",
                       title="Demand (reviews/month) vs. Price by Borough",
                       color_continuous_scale="Viridis", size_max=40)
    fig6.update_layout(height=550)
    st.plotly_chart(fig6, use_container_width=True)
    st.dataframe(demand, hide_index=True, use_container_width=True)
    st.caption(
        "Demand is proxied by average reviews per month (no real booking/occupancy data is "
        "available in this export)."
    )
