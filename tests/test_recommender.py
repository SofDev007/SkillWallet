from datetime import date

from planner import recommender
from planner.llm import LLMClient
from planner.config import PROVIDER_DEMO


def prefs(**overrides):
    base = dict(vibe="Beach", days=4, start_date=date(2026, 12, 10).isoformat(), budget="Moderate", party="Couple",
                travellers=2, pace="Moderate", interests=["Food"], diet="No preference", region="Anywhere")
    base.update(overrides)
    return base


def test_beach_vibe_recommends_beach_cities():
    recs = recommender.recommend_offline(prefs())
    assert len(recs) == 3
    assert recs[0]["city"] in {"Goa", "Bali", "Kochi", "Dubai"}
    assert all(0 <= r["match_score"] <= 100 for r in recs)


def test_mountain_vibe():
    recs = recommender.recommend_offline(prefs(vibe="Mountains", start_date=date(2027, 5, 10).isoformat()))
    assert {r["city"] for r in recs} >= {"Manali"}


def test_region_filter():
    india = recommender.recommend_offline(prefs(region="India only"))
    intl = recommender.recommend_offline(prefs(region="International only"))
    assert all(r["country"] == "India" for r in india)
    assert all(r["country"] != "India" for r in intl)


def test_off_season_is_penalised():
    goa = recommender.data.DESTINATIONS["Goa"]
    peak, _ = recommender.score_destination(goa, prefs(start_date=date(2026, 12, 1).isoformat()))
    monsoon, reasons = recommender.score_destination(goa, prefs(start_date=date(2027, 7, 1).isoformat()))
    assert peak > monsoon
    assert any("monsoon" in r.lower() for r in reasons)


def test_demo_client_uses_offline_paths():
    client = LLMClient(PROVIDER_DEMO)
    recs, warning = recommender.recommend(prefs(), client)
    assert recs and warning is None
    profile, warning = recommender.resolve_profile("goa", prefs(), client)
    assert profile["name"] == "Goa" and warning is None
    profile, warning = recommender.resolve_profile("Reykjavik", prefs(), client)
    assert profile["source"] == "generic" and "template" in warning
