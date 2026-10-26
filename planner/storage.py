"""Trip persistence.

Default: a local SQLite database (zero external dependencies, works on Streamlit
Community Cloud). Optional: Supabase (PostgreSQL) through its REST API when
``SUPABASE_URL`` and ``SUPABASE_KEY`` are configured — any Supabase failure falls
back to SQLite automatically.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

import requests

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "trips.db"

SCHEMA = """
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
"""

LIST_COLUMNS = ["id", "title", "destination", "country", "start_date", "days", "budget_level",
                "party", "travellers", "total_inr", "provider", "created_at", "updated_at"]


def _row(trip: dict) -> dict:
    prefs = trip["preferences"]
    now = datetime.now().isoformat(timespec="seconds")
    return {
        "id": trip["id"],
        "title": trip.get("title") or trip["destination"]["name"],
        "destination": trip["destination"]["name"],
        "country": trip["destination"].get("country", ""),
        "start_date": str(prefs.get("start_date", "")),
        "days": len(trip["days"]),
        "budget_level": prefs.get("budget"),
        "party": prefs.get("party"),
        "travellers": int(prefs.get("travellers", 1)),
        "total_inr": float(trip["summary"].get("total_inr", 0)),
        "provider": trip.get("provider", ""),
        "payload": json.dumps(trip, ensure_ascii=False),
        "created_at": trip.get("created_at") or now,
        "updated_at": now,
    }


class SQLiteTripStore:
    backend = "SQLite"

    def __init__(self, path: str | Path = DEFAULT_DB_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn, conn:
            conn.executescript(SCHEMA)

    @property
    def location(self) -> str:
        return str(self.path.name)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def save(self, trip: dict) -> str:
        row = _row(trip)
        with closing(self._connect()) as conn, conn:
            existing = conn.execute("SELECT created_at FROM trips WHERE id = ?", (row["id"],)).fetchone()
            if existing:
                row["created_at"] = existing["created_at"]
            conn.execute(
                f"INSERT OR REPLACE INTO trips ({', '.join(row)}) VALUES ({', '.join('?' * len(row))})",
                tuple(row.values()),
            )
            conn.execute("DELETE FROM trip_activities WHERE trip_id = ?", (row["id"],))
            conn.executemany(
                "INSERT INTO trip_activities (trip_id, day, slot, start_time, place_name, category, lat, lon, cost_local)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (row["id"], d["day"], s["slot"], s["start"], s["place"]["name"],
                     s["place"].get("category", "restaurant" if s["kind"] == "meal" else ""),
                     s["place"]["lat"], s["place"]["lon"], s["cost_local"])
                    for d in trip["days"] for s in d["slots"]
                ],
            )
        return row["id"]

    def list(self) -> list[dict]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                f"SELECT {', '.join(LIST_COLUMNS)} FROM trips ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def load(self, trip_id: str) -> dict | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT payload FROM trips WHERE id = ?", (trip_id,)).fetchone()
        return json.loads(row["payload"]) if row else None

    def delete(self, trip_id: str) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM trips WHERE id = ?", (trip_id,))

    def stats(self) -> dict:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS trips, COALESCE(SUM(days), 0) AS days,"
                " COUNT(DISTINCT destination) AS destinations FROM trips"
            ).fetchone()
            acts = conn.execute("SELECT COUNT(*) AS n FROM trip_activities").fetchone()
        return {"trips": row["trips"], "days": row["days"], "destinations": row["destinations"], "activities": acts["n"]}


class SupabaseTripStore:
    """Minimal PostgREST client for the ``trips`` table defined in db/supabase_schema.sql."""

    backend = "Supabase"

    def __init__(self, url: str, key: str, timeout: int = 15):
        self.base = url.rstrip("/") + "/rest/v1"
        self.headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        self.timeout = timeout
        self.list()  # fail fast if the table or credentials are wrong

    @property
    def location(self) -> str:
        return self.base.split("//")[-1].split(".")[0]

    def _req(self, method: str, path: str, **kwargs) -> requests.Response:
        resp = requests.request(method, f"{self.base}/{path}", headers={**self.headers, **kwargs.pop("headers", {})},
                                timeout=self.timeout, **kwargs)
        resp.raise_for_status()
        return resp

    def save(self, trip: dict) -> str:
        row = _row(trip)
        row["payload"] = trip  # stored as JSONB
        self._req("POST", "trips", json=row, headers={"Prefer": "resolution=merge-duplicates"})
        return row["id"]

    def list(self) -> list[dict]:
        resp = self._req("GET", "trips", params={"select": ",".join(LIST_COLUMNS), "order": "updated_at.desc"})
        return resp.json()

    def load(self, trip_id: str) -> dict | None:
        resp = self._req("GET", "trips", params={"select": "payload", "id": f"eq.{trip_id}"})
        rows = resp.json()
        if not rows:
            return None
        payload = rows[0]["payload"]
        return json.loads(payload) if isinstance(payload, str) else payload

    def delete(self, trip_id: str) -> None:
        self._req("DELETE", "trips", params={"id": f"eq.{trip_id}"})

    def stats(self) -> dict:
        rows = self.list()
        return {"trips": len(rows), "days": sum(int(r.get("days") or 0) for r in rows),
                "destinations": len({r.get("destination") for r in rows}), "activities": None}


def get_store(supabase_url: str = "", supabase_key: str = "", db_path: str | Path | None = None):
    """Return (store, warning). Prefers Supabase when configured, else SQLite."""
    url = supabase_url or os.getenv("SUPABASE_URL", "")
    key = supabase_key or os.getenv("SUPABASE_KEY", "")
    if url and key:
        try:
            return SupabaseTripStore(url, key), None
        except (requests.RequestException, ValueError) as exc:
            return SQLiteTripStore(db_path or DEFAULT_DB_PATH), f"Supabase unavailable ({type(exc).__name__}); using local SQLite."
    return SQLiteTripStore(db_path or DEFAULT_DB_PATH), None
