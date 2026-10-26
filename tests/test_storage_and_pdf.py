from datetime import date

from planner import data
from planner.itinerary import build_trip
from planner.pdf_export import build_pdf
from planner.storage import SQLiteTripStore


def make_trip(city="Kochi"):
    prefs = dict(destination=city, vibe="Cultural", days=3, start_date=date(2027, 1, 5).isoformat(), budget="Budget",
                 party="Family", travellers=4, pace="Relaxed", interests=["History", "Food"], diet="Vegetarian",
                 region="Anywhere", budget_cap_inr=50000)
    return build_trip(data.get_destination(city), prefs)


def test_sqlite_roundtrip(tmp_path):
    store = SQLiteTripStore(tmp_path / "trips.db")
    trip = make_trip()
    store.save(trip)
    trip["title"] = "Renamed"
    store.save(trip)  # upsert, not duplicate
    rows = store.list()
    assert len(rows) == 1 and rows[0]["title"] == "Renamed"
    loaded = store.load(trip["id"])
    assert loaded["days"] == trip["days"]
    stats = store.stats()
    assert stats["trips"] == 1 and stats["activities"] == sum(len(d["slots"]) for d in trip["days"])
    store.delete(trip["id"])
    assert store.list() == [] and store.stats()["activities"] == 0


def test_pdf_is_generated_for_every_destination():
    for city in data.list_destinations():
        pdf = build_pdf(make_trip(city))
        assert pdf.startswith(b"%PDF") and len(pdf) > 3000


def test_pdf_handles_unicode_and_markup_in_names():
    trip = make_trip()
    trip["days"][0]["slots"][0]["place"]["name"] = "Café <Zürich> & “Smart” — ₹ 東京"
    assert build_pdf(trip).startswith(b"%PDF")
