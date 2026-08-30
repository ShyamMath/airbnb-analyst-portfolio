# London Airbnb Market Research

69,351 real Airbnb listings across all 33 London boroughs, taken through a full analyst pipeline: clean → SQL database → Python analysis → notebook → interactive dashboard → written report.

Start here: [`reports/research_report.md`](reports/research_report.md)
Full walkthrough: [`notebooks/research_analysis.ipynb`](notebooks/research_analysis.ipynb)
Dashboard: `dashboard/app.py` (live map, filters — run instructions below)

## What it found

- Central boroughs cost 2.6x more than the cheapest outer ones (City of London £196 median vs. ~£75-80 outer)
- 45.9% of listings belong to hosts running more than one property, and the "6+ listings" tier charges 2.4x what single-listing hosts do
- 8.1% of listings look commercial by a documented heuristic (entire-home + multi-listing host + near-year-round availability) — that jumps to 28.8% in the City of London alone
- Guest demand doesn't track price cleanly — a few outer boroughs (Hillingdon, Croydon, Bexley) get above-average demand at below-average prices

This is real Kaggle data (Inside Airbnb London), not a toy dataset — so the cleaning step actually mattered: two fully-empty columns, £0 pricing errors, and a heavy right skew in prices all needed a decision, and those decisions are documented in `src/clean_data.py`, not hidden.

## Structure

```
airbnb-analyst-portfolio/
├── data/
│   ├── raw/listings_raw.csv          # original Kaggle export
│   ├── processed/listings_clean.csv  # cleaned + feature-engineered
│   └── database/airbnb.db
├── sql/
│   ├── schema.sql                    # listings + hosts tables
│   └── analysis_queries.sql          # window functions, CTEs, joins
├── src/
│   ├── clean_data.py                 # cleaning + feature engineering
│   ├── load_to_db.py                 # CSV -> SQLite, builds the hosts table
│   ├── metrics.py                    # pricing, concentration, demand functions
│   └── analysis.py                   # runs everything, saves charts
├── notebooks/
│   ├── build_notebook.py             # generates the notebook from code
│   └── research_analysis.ipynb
├── dashboard/
│   └── app.py                        # Streamlit dashboard with a live map
├── reports/
│   └── research_report.md
└── outputs/
    ├── figures/
    └── *.csv                         # summary tables
```

## Running it

```bash
pip install -r requirements.txt
python3 src/clean_data.py
python3 src/load_to_db.py
python3 src/analysis.py          # prints summaries, saves charts to outputs/figures/
streamlit run dashboard/app.py
```

Regenerate the notebook after touching `src/`: `python3 notebooks/build_notebook.py`

## What's in it

- Data cleaning with actual judgment calls, not a pre-cleaned CSV: fully-null columns dropped, £0-price errors flagged, outliers capped rather than deleted
- A "likely commercial" listing flag — engineered, documented, and explicitly called a heuristic rather than a legal fact
- A hosts table rolled up from listings (a real one-to-many join, not one flat table)
- SQL window functions to compute medians and percentile ranks (SQLite has no MEDIAN())
- The Herfindahl-Hirschman Index, borrowed from antitrust analysis, applied to host market share
- A live interactive map in the dashboard, not just static charts
- A written report with an executive summary, numbers, and stated limitations

## Ideas to build on this

- Price-prediction model (borough, room type, availability) as a regression exercise
- Cross-check `likely_commercial` boroughs against real London short-let licensing data
- Deploy the dashboard on Streamlit Community Cloud and link it from your resume
