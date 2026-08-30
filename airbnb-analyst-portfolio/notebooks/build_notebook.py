"""Builds research_analysis.ipynb from code, so it stays in sync with src/.
Re-run this after changing clean_data.py, metrics.py, or analysis.py."""
import nbformat as nbf
from pathlib import Path

nb = nbf.v4.new_notebook()
cells = []

def md(text):
    cells.append(nbf.v4.new_markdown_cell(text))

def code(text):
    cells.append(nbf.v4.new_code_cell(text))

md("""# London Airbnb Market Research
### Pricing, host concentration, and commercial listings across 33 boroughs

**Dataset:** Inside Airbnb London listings export (Kaggle), 69,351 listings
**Author:** [Your Name] · **Date:** [Report Date]
""")

code("""import sys
sys.path.insert(0, '../src')

import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from metrics import (
    robust_price_stats, host_concentration_index,
    commercial_listing_summary, demand_supply_view
)

sns.set_theme(style='whitegrid', context='notebook')
pd.set_option('display.max_columns', None)

DB_PATH = '../data/database/airbnb.db'
conn = sqlite3.connect(DB_PATH)
""")

md("## 1. Load cleaned data\nRaw CSV had two fully-null columns (`neighbourhood_group`, `license`), 19 zero-price listings, and heavy price outliers - all handled in `src/clean_data.py`. Loading the cleaned data from the database here.")

code("""listings = pd.read_sql('SELECT * FROM listings', conn, parse_dates=['last_review'])
hosts = pd.read_sql('SELECT * FROM hosts', conn)

print(f'{len(listings):,} listings across {listings[\"neighbourhood\"].nunique()} boroughs')
print(f'{listings[\"host_id\"].nunique():,} unique hosts')
listings.head()
""")

md("## 2. Data quality at a glance")

code("""print('Zero-price listings (data errors, excluded from price stats):', listings['is_zero_price'].sum())
print('Price outliers (>99th percentile, flagged not dropped):', listings['is_price_outlier'].sum())
print('Listings with no reviews yet:', (~listings['has_reviews'].astype(bool)).sum(),
      f\"({(~listings['has_reviews'].astype(bool)).mean()*100:.1f}%)\")
""")

md("## 3. Pricing by borough\nPrice is heavily right-skewed, so **median** (not mean) is used throughout.")

code("""price_stats = robust_price_stats(listings, 'neighbourhood')
price_stats.head(10)
""")

code("""top15 = price_stats.head(15)
fig, ax = plt.subplots(figsize=(10,7))
sns.barplot(data=top15, y='neighbourhood', x='median_price', hue='neighbourhood', palette='viridis', legend=False, ax=ax)
ax.set_title('Median Price by Borough (Top 15)')
ax.set_xlabel('Median Price (£/night)')
ax.set_ylabel('')
plt.tight_layout()
plt.show()
""")

md("## 4. Room type mix\nEntire homes cost more than private/shared rooms, as expected - the question is by how much.")

code("""clean = listings[listings['is_price_outlier']==0]
fig, ax = plt.subplots(figsize=(8,6))
order = clean.groupby('room_type')['price'].median().sort_values(ascending=False).index
sns.boxplot(data=clean, x='room_type', y='price', order=order, hue='room_type', palette='mako', legend=False, showfliers=False, ax=ax)
ax.set_title('Price by Room Type')
plt.tight_layout()
plt.show()

clean.groupby('room_type')['price'].median().sort_values(ascending=False)
""")

md("## 5. Host concentration\nUsing the Herfindahl-Hirschman Index (HHI), a standard concentration metric from antitrust analysis, to see how much of the market sits with a few hosts vs. many.")

code("""concentration = host_concentration_index(listings)
concentration
""")

md("""An HHI this low means no single host dominates. But `multi_listing_host_share_pct` tells a
different story - it's the share of *all listings* owned by hosts with more than one property,
which is the better lens on how "professionalized" the platform actually is.""")

code("""tier_counts = listings['host_tier'].value_counts()
order = ['Single listing', '2 listings', '3-5 listings', '6+ listings (professional)']
tier_counts = tier_counts.reindex(order)

tier_avg_price = clean.groupby('host_tier')['price'].mean().reindex(order)

fig, axes = plt.subplots(1,2, figsize=(13,5))
axes[0].pie(tier_counts, labels=tier_counts.index, autopct='%1.1f%%', colors=sns.color_palette('viridis',4))
axes[0].set_title('Share of Listings by Host Tier')
sns.barplot(x=tier_avg_price.index, y=tier_avg_price.values, hue=tier_avg_price.index, palette='mako', legend=False, ax=axes[1])
axes[1].set_title('Avg Price by Host Tier')
axes[1].tick_params(axis='x', rotation=20)
plt.tight_layout()
plt.show()
""")

md("## 6. Likely-commercial listings\nA listing is flagged *likely commercial* if it's an entire home/apt, the host runs 2+ listings, and it's available 270+ days/year. It's a heuristic, not a legal determination - just a way to approximate managed-rental activity vs. genuine home-sharing.")

code("""commercial = commercial_listing_summary(listings)
commercial.head(10)
""")

code("""top15_commercial = commercial.head(15)
fig, ax = plt.subplots(figsize=(10,7))
sns.barplot(data=top15_commercial, y='neighbourhood', x='pct_commercial', hue='neighbourhood', palette='rocket', legend=False, ax=ax)
ax.set_title('Likely-Commercial Listing Share by Borough (Top 15)')
ax.set_xlabel('% Flagged Likely Commercial')
plt.tight_layout()
plt.show()
""")

md("## 7. Demand vs. price\nNo real booking data exists in this export, so `reviews_per_month` stands in for demand - more completed stays roughly means more reviews.")

code("""demand = demand_supply_view(listings)
demand.head(10)
""")

code("""fig, ax = plt.subplots(figsize=(8,7))
sc = ax.scatter(demand['avg_price'], demand['avg_reviews_per_month'], s=demand['n_listings']/15,
                 c=demand['n_listings'], cmap='viridis', alpha=0.7, edgecolor='black')
for _, row in demand.iterrows():
    if row['n_listings'] > 1000 or row['avg_reviews_per_month'] > 0.85:
        ax.annotate(row['neighbourhood'], (row['avg_price'], row['avg_reviews_per_month']), xytext=(5,5), textcoords='offset points', fontsize=9)
plt.colorbar(sc, label='Number of Listings')
ax.set_xlabel('Average Price (£/night)')
ax.set_ylabel('Avg Reviews/Month (demand proxy)')
ax.set_title('Demand vs. Price by Borough')
plt.tight_layout()
plt.show()
""")

md("""## 8. Key findings

1. **Central boroughs command a clear price premium.** City of London, Kensington & Chelsea, and Westminster top the median-price ranking, consistent with prime location value.
2. **The market is meaningfully "professionalized."** Roughly 46% of listings belong to hosts with more than one listing, and hosts with 6+ listings charge nearly 2.4x the average price of single-listing hosts.
3. **Likely-commercial listings cluster in specific boroughs**, led by City of London (~29%) and Westminster (~15%) — both dense, high-tourist-traffic areas where short-let regulation debates are most active.
4. **Demand (reviews/month) doesn't map one-to-one with price** — some lower-priced outer boroughs post above-average review activity relative to their listing volume, suggesting under-served or highly efficient markets worth a closer look.

## 9. Recommendation / Next Steps

For a host-facing product or a market-entry analysis, the data suggests: (a) central boroughs support premium pricing but face the most competitive, professionalized supply; (b) several outer boroughs show a favorable demand-to-price ratio and lower professionalization, which may represent an easier entry point for new hosts; (c) any policy or platform-integrity analysis should treat `likely_commercial` boroughs (esp. City of London, Westminster) as the priority segment for further investigation, since our heuristic can only approximate — not confirm — commercial-use classification.

---
*See `reports/research_report.md` for the full written report and `dashboard/app.py` for an interactive version of this analysis.*
""")

nb['cells'] = cells
out_path = Path(__file__).resolve().parent / "research_analysis.ipynb"
nbf.write(nb, out_path)
print(f"Notebook written to {out_path}")
