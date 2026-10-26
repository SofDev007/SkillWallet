-- SQLite schema used by planner/storage.py (created automatically on first run).
CREATE TABLE IF NOT EXISTS trips (
    id            TEXT PRIMARY KEY,
    title         TEXT NOT NULL,
    destination   TEXT NOT NULL,
    country       TEXT,
    start_date    TEXT,
    days          INTEGER NOT NULL,
    budget_level  TEXT,
    party         TEXT,
    travellers    INTEGER,
    total_inr     REAL,
    provider      TEXT,
    payload       TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS trip_activities (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id     TEXT NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    day         INTEGER NOT NULL,
    slot        TEXT NOT NULL,
    start_time  TEXT,
    place_name  TEXT NOT NULL,
    category    TEXT,
    lat         REAL,
    lon         REAL,
    cost_local  REAL
);
CREATE INDEX IF NOT EXISTS idx_activities_trip ON trip_activities(trip_id);
CREATE INDEX IF NOT EXISTS idx_trips_created ON trips(created_at);
