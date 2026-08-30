-- listings is the main table; hosts is rolled up from it (one host -> many listings)

DROP TABLE IF EXISTS listings;
CREATE TABLE listings (
    id                              INTEGER PRIMARY KEY,
    name                            TEXT,
    host_id                         INTEGER NOT NULL,
    host_name                       TEXT,
    neighbourhood                   TEXT NOT NULL,
    latitude                        REAL,
    longitude                       REAL,
    room_type                       TEXT,
    price                           REAL,
    price_capped                    REAL,
    is_zero_price                   INTEGER,
    is_price_outlier                INTEGER,
    minimum_nights                  INTEGER,
    number_of_reviews               INTEGER,
    last_review                     TEXT,
    reviews_per_month               REAL,
    calculated_host_listings_count  INTEGER,
    availability_365                INTEGER,
    availability_tier               TEXT,
    number_of_reviews_ltm           INTEGER,
    has_reviews                     INTEGER,
    days_since_last_review          REAL,
    host_tier                       TEXT,
    likely_commercial               INTEGER
);

CREATE INDEX idx_listings_neighbourhood ON listings(neighbourhood);
CREATE INDEX idx_listings_room_type ON listings(room_type);
CREATE INDEX idx_listings_host_id ON listings(host_id);

DROP TABLE IF EXISTS hosts;
CREATE TABLE hosts (
    host_id             INTEGER PRIMARY KEY,
    host_name           TEXT,
    total_listings      INTEGER,
    total_reviews       INTEGER,
    avg_price           REAL,
    boroughs_active_in  INTEGER,
    host_tier           TEXT
);

CREATE INDEX idx_hosts_tier ON hosts(host_tier);
