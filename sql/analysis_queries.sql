-- Run these against data/database/airbnb.db, one at a time or all together.

-- 1. Median price by borough. SQLite has no MEDIAN(), so this ranks each
--    borough's prices and picks the middle row(s) with a window function.
WITH ranked AS (
    SELECT neighbourhood, price,
           ROW_NUMBER() OVER (PARTITION BY neighbourhood ORDER BY price) AS rn,
           COUNT(*) OVER (PARTITION BY neighbourhood) AS cnt
    FROM listings
    WHERE is_price_outlier = 0
)
SELECT neighbourhood,
       cnt AS n_listings,
       ROUND(AVG(price), 2) AS median_price
FROM ranked
WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
GROUP BY neighbourhood
ORDER BY median_price DESC;

-- 2. Room type mix and average price by borough
SELECT
    neighbourhood,
    room_type,
    COUNT(*) AS n_listings,
    ROUND(AVG(price), 2) AS avg_price
FROM listings
WHERE is_price_outlier = 0
GROUP BY neighbourhood, room_type
ORDER BY neighbourhood, n_listings DESC;

-- 3. Host concentration: share of all listings owned by multi-listing hosts
SELECT
    host_tier,
    COUNT(*) AS n_listings,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM listings), 2) AS pct_of_all_listings,
    ROUND(AVG(price), 2) AS avg_price
FROM listings
GROUP BY host_tier
ORDER BY n_listings DESC;

-- 4. Likely-commercial listings by borough
SELECT
    neighbourhood,
    COUNT(*) AS total_listings,
    SUM(likely_commercial) AS commercial_listings,
    ROUND(100.0 * SUM(likely_commercial) / COUNT(*), 2) AS pct_commercial
FROM listings
GROUP BY neighbourhood
ORDER BY pct_commercial DESC;

-- 5. Top 15 hosts by listing count
SELECT host_id, host_name, total_listings, boroughs_active_in, avg_price
FROM hosts
ORDER BY total_listings DESC
LIMIT 15;

-- 6. Avg reviews/month by borough vs avg price (demand proxy)
SELECT
    neighbourhood,
    ROUND(AVG(reviews_per_month), 2) AS avg_reviews_per_month,
    ROUND(AVG(price), 2) AS avg_price,
    COUNT(*) AS n_listings
FROM listings
WHERE is_price_outlier = 0
GROUP BY neighbourhood
ORDER BY avg_reviews_per_month DESC;

-- 7. Minimum-nights buckets
SELECT
    CASE
        WHEN minimum_nights <= 3  THEN '1-3 nights (short-let)'
        WHEN minimum_nights <= 7  THEN '4-7 nights'
        WHEN minimum_nights <= 29 THEN '8-29 nights'
        ELSE '30+ nights (long-let)'
    END AS min_nights_bucket,
    COUNT(*) AS n_listings,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM listings), 2) AS pct_of_all_listings
FROM listings
GROUP BY min_nights_bucket
ORDER BY n_listings DESC;

-- 8. Price percentile rank within each borough
SELECT
    id, name, neighbourhood, room_type, price,
    ROUND(PERCENT_RANK() OVER (PARTITION BY neighbourhood ORDER BY price) * 100, 1) AS price_percentile_in_borough
FROM listings
WHERE is_price_outlier = 0
ORDER BY neighbourhood, price;
