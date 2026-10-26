from datetime import date

import pytest

from planner import data
from planner.config import FULL_DAY_HOURS, PACE_SLOTS, PACES, SLOT_DINNER, SLOT_LUNCH, SLOT_MORNING
from planner.itinerary import (
    balanced_clusters, build_trip, exchange_slots, find_replacement, apply_swap, parse_instruction,
    regenerate_day, used_ids,
)


def prefs(**overrides):
    base = dict(destination="Goa", vibe="Beach", days=4, start_date=date(2026, 12, 10).isoformat(), budget="Moderate",
                party="Couple", travellers=2, pace="Moderate", interests=["Food", "History"], diet="No preference",
                region="Anywhere", budget_cap_inr=0)
    base.update(overrides)
    return base


@pytest.mark.parametrize("city", data.list_destinations())
@pytest.mark.parametrize("pace", PACES)
@pytest.mark.parametrize("days", [1, 3, 7, 14])
def test_every_destination_builds(city, pace, days):
    trip = build_trip(data.get_destination(city), prefs(pace=pace, days=days))
    assert len(trip["days"]) == days
    for day in trip["days"]:
        names = [s["slot"] for s in day["slots"]]
        assert names[0] == SLOT_MORNING
        assert SLOT_LUNCH in names and SLOT_DINNER in names
        assert day["total_local"] >= 0
    assert trip["summary"]["total_local"] == pytest.approx(sum(d["total_local"] for d in trip["days"]), rel=1e-6)


def test_no_attraction_repeats_and_dates_are_sequential():
    trip = build_trip(data.get_destination("Paris"), prefs(destination="Paris", days=5))
    acts = [s["place"]["id"] for d in trip["days"] for s in d["slots"]
            if s["kind"] == "activity" and not s["place"].get("generic")]
    assert len(acts) == len(set(acts))
    dates = [d["date"] for d in trip["days"]]
    assert dates[0] == "2026-12-10" and dates[-1] == "2026-12-14"


def test_pace_controls_activity_count():
    for pace, (m, a) in PACE_SLOTS.items():
        trip = build_trip(data.get_destination("Rome"), prefs(destination="Rome", pace=pace, days=2))
        day = trip["days"][0]
        if not any(s["place"].get("duration", 0) >= FULL_DAY_HOURS for s in day["slots"]):
            assert sum(1 for s in day["slots"] if s["slot"] == SLOT_MORNING) == m


def test_clustering_is_balanced_and_complete():
    places = data.get_destination("Tokyo")["places"]
    groups = balanced_clusters(places, 4)
    assert len(groups) == 4
    assert sum(len(g) for g in groups) == len(places)
    assert max(len(g) for g in groups) <= -(-len(places) // 4)


@pytest.mark.parametrize("city", ["Goa", "Paris", "Tokyo", "Rome", "Bangkok"])
def test_clustering_beats_unclustered_route(city):
    trip = build_trip(data.get_destination(city), prefs(destination=city, days=4))
    # Sunset stops are pinned to the end of a day, so allow a hair of slack.
    assert trip["summary"]["route_km"] <= trip["summary"]["naive_route_km"] * 1.02


def test_budget_scales_with_travellers_and_level():
    solo = build_trip(data.get_destination("Jaipur"), prefs(destination="Jaipur", party="Solo", travellers=1))
    group = build_trip(data.get_destination("Jaipur"), prefs(destination="Jaipur", party="Friends", travellers=4))
    lux = build_trip(data.get_destination("Jaipur"), prefs(destination="Jaipur", party="Solo", travellers=1, budget="Luxury"))
    assert group["summary"]["total_local"] > solo["summary"]["total_local"]
    assert lux["summary"]["by_category"]["stay"] > solo["summary"]["by_category"]["stay"]


def test_budget_cap_flag():
    trip = build_trip(data.get_destination("Dubai"), prefs(destination="Dubai", budget_cap_inr=1000))
    assert trip["summary"]["over_budget"] is True


def test_vegetarian_preference_prefers_veg_restaurants():
    trip = build_trip(data.get_destination("Mumbai"), prefs(destination="Mumbai", diet="Vegetarian"))
    meals = [s["place"] for d in trip["days"] for s in d["slots"] if s["kind"] == "meal" and not s["place"].get("generic")]
    veg = [m for m in meals if {"vegetarian", "vegan"} & set(m["tags"])]
    assert len(veg) >= len(meals) / 2


def test_parse_instruction_reads_target_after_for():
    want = parse_instruction("Swap museum for outdoor market")
    assert "market" in want["tags"] and want["outdoor"]
    assert "museum" not in want["tags"]


def test_swap_lunch_to_vegetarian():
    trip = build_trip(data.get_destination("Bali"), prefs(destination="Bali", days=2))
    lunch_idx = next(i for i, s in enumerate(trip["days"][0]["slots"]) if s["slot"] == SLOT_LUNCH)
    place, matched, origin = find_replacement(trip, 0, lunch_idx, "Find a vegetarian lunch spot")
    assert place and matched and origin is None
    assert {"vegetarian", "vegan"} & set(place["tags"])
    apply_swap(trip, 0, lunch_idx, place)
    assert trip["days"][0]["slots"][lunch_idx]["place"]["id"] == place["id"]


def test_swap_borrows_from_another_day_when_pool_exhausted():
    trip = build_trip(data.get_destination("Jaipur"), prefs(destination="Jaipur", days=4))
    before = sorted(used_ids(trip))
    place, matched, origin = find_replacement(trip, 0, 0, "swap for outdoor market")
    assert place is not None and origin is not None
    exchange_slots(trip, (0, 0), origin)
    assert sorted(used_ids(trip)) == before  # same stops, just traded


def test_regenerate_day_leaves_other_days_untouched():
    trip = build_trip(data.get_destination("Interlaken"), prefs(destination="Interlaken", days=3, interests=["Nature"]))
    untouched = [[s["place"]["id"] for s in d["slots"]] for i, d in enumerate(trip["days"]) if i != 1]
    regenerate_day(trip, 1, "Adventure day", seed=3)
    after = [[s["place"]["id"] for s in d["slots"]] for i, d in enumerate(trip["days"]) if i != 1]
    assert untouched == after
    assert trip["days"][1]["focus"] == "Adventure day"


def test_generic_destination_still_plans():
    trip = build_trip(data.generic_destination("Atlantis"), prefs(destination="Atlantis", days=3))
    assert len(trip["days"]) == 3
    assert trip["destination"]["source"] == "generic"
