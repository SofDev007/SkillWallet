"""Day-by-day itinerary engine.

Pipeline:
1. Rank the destination's attractions against the traveller's preferences.
2. Give long excursions (>= FULL_DAY_HOURS) a day of their own.
3. Group the remaining attractions into one geographic cluster per day with a
   capacity-balanced k-means, so each day stays inside one area.
4. Order each day's stops with a nearest-neighbour route from the hotel (city centre).
5. Attach lunch/dinner (and optional evening entertainment) close to where you are.
6. Schedule times, then cost everything and build a running budget.
"""

from __future__ import annotations

import copy
import random
import uuid
from itertools import permutations
from datetime import date, datetime, timedelta

from .config import (
    BUDGET_TARGET_TIER, CITY_SPEED_KMH, DINNER_DURATION, DINNER_EARLIEST, EVENING_DURATION,
    EVENING_SEARCH_RADIUS_KM, FULL_DAY_HOURS, INTEREST_CATEGORIES, INTEREST_TAGS, LUNCH_DURATION,
    LUNCH_EARLIEST, MEAL_SEARCH_RADIUS_KM, PACE_SLOTS, PACE_START_HOUR, SCHEMA_VERSION, SLOT_AFTERNOON,
    SLOT_DINNER, SLOT_EVENING, SLOT_LUNCH, SLOT_MORNING, VIBE_CATEGORIES,
)
from .utils import centroid, convert, fmt_hour, road_km, round_minutes, usd_per_unit

MEAL_SLOTS = {SLOT_LUNCH, SLOT_DINNER}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def _travel_month(prefs: dict) -> int:
    try:
        return date.fromisoformat(str(prefs.get("start_date"))).month
    except (TypeError, ValueError):
        return date.today().month


def score_place(place: dict, prefs: dict, profile: dict, focus: str | None = None) -> float:
    """Preference fit of one attraction. Higher is better."""
    interests = prefs.get("interests") or []
    tags = set(place.get("tags", []))
    cat = place["category"]
    s = 1.0
    for interest in interests:
        if cat in INTEREST_CATEGORIES.get(interest, set()):
            s += 3.0
        if tags & INTEREST_TAGS.get(interest, set()):
            s += 1.0
    vibe = prefs.get("vibe")
    if vibe in VIBE_CATEGORIES and cat in VIBE_CATEGORIES[vibe]:
        s += 1.5
    if "iconic" in tags:
        s += 2.0
    if "unesco" in tags:
        s += 0.5

    party = prefs.get("party")
    if party == "Family":
        s += 1.0 if "family" in tags else 0.0
        s -= 3.0 if cat == "nightlife" else 0.0
    elif party == "Couple":
        s += 1.0 if tags & {"romantic", "sunset"} else 0.0
    elif party == "Friends":
        s += 1.0 if cat in {"nightlife", "adventure"} else 0.0
    elif party == "Solo":
        s += 0.5 if "walking" in tags else 0.0

    budget = prefs.get("budget")
    paid = sorted(p["cost"] for p in profile["places"] if p["cost"] > 0)
    median = paid[len(paid) // 2] if paid else 0
    if budget == "Budget":
        s += 0.5 if place["cost"] == 0 else 0.0
        s -= 1.5 if median and place["cost"] > 3 * median else 0.0
    elif budget == "Luxury":
        s += 1.0 if "luxury" in tags else 0.0

    if _travel_month(prefs) in profile.get("avoid_months", {}) and not place.get("indoor"):
        s -= 0.75

    pace = prefs.get("pace")
    if pace == "Relaxed" and place["duration"] > 4:
        s -= 1.0
    if pace == "Fast-Paced" and place["duration"] <= 1.5:
        s += 0.5

    if focus:
        s += _focus_bonus(place, focus)
    return s


DAY_FOCUS = {
    "Keep it balanced": set(),
    "Adventure day": {"adventure"},
    "Culture & history": {"history", "culture"},
    "Food trail": {"food"},
    "Nature & outdoors": {"nature", "beach"},
    "Shopping spree": {"shopping"},
    "Relax & unwind": {"wellness", "beach", "nature"},
}


def _focus_bonus(place: dict, focus: str) -> float:
    cats = DAY_FOCUS.get(focus, set())
    bonus = 4.0 if place["category"] in cats else 0.0
    if focus == "Relax & unwind":
        bonus -= 1.0 * max(0.0, place["duration"] - 2)
    return bonus


# ---------------------------------------------------------------------------
# Geography
# ---------------------------------------------------------------------------
def balanced_clusters(points: list[dict], k: int, seed: int = 7, iterations: int = 12) -> list[list[dict]]:
    """Capacity-balanced k-means on lat/lon. Returns exactly ``k`` (possibly empty) groups."""
    if k <= 0:
        return []
    if not points:
        return [[] for _ in range(k)]
    if k == 1:
        return [list(points)]
    rng = random.Random(seed)
    capacity = -(-len(points) // k)

    # k-means++ seeding (deterministic for a given seed).
    centres = [dict(rng.choice(points))]
    while len(centres) < min(k, len(points)):
        dists = [min(road_km(p, c) for c in centres) ** 2 for p in points]
        total = sum(dists)
        if total == 0:
            break
        pick, acc = rng.random() * total, 0.0
        for p, d in zip(points, dists):
            acc += d
            if acc >= pick:
                centres.append(dict(p))
                break
    while len(centres) < k:
        centres.append(dict(centres[-1]))

    groups: list[list[dict]] = [[] for _ in range(k)]
    for _ in range(iterations):
        pairs = sorted(
            ((road_km(p, c), i, j) for i, p in enumerate(points) for j, c in enumerate(centres)),
            key=lambda t: t[0],
        )
        assigned: dict[int, int] = {}
        groups = [[] for _ in range(k)]
        for _, i, j in pairs:
            if i in assigned or len(groups[j]) >= capacity:
                continue
            assigned[i] = j
            groups[j].append(points[i])
        new_centres = [centroid(g) if g else centres[j] for j, g in enumerate(groups)]
        if all(road_km(a, b) < 0.01 for a, b in zip(centres, new_centres)):
            break
        centres = new_centres
    return groups


def nearest_neighbour_route(stops: list[dict], start: dict) -> list[dict]:
    """Shortest hotel -> stops -> hotel loop (exact for small days, nearest-neighbour otherwise).

    Sunset spots are always kept at the end of the day.
    """
    late = [p for p in stops if "sunset" in p.get("tags", [])]
    early = [p for p in stops if p not in late]
    if len(stops) <= 6:
        best, best_km = None, float("inf")
        for e in permutations(early):
            for l in permutations(late):
                order = [*e, *l]
                km = route_distance(order, start)
                if km < best_km:
                    best, best_km = order, km
        return list(best or [])
    remaining, route, here = list(early), [], start
    while remaining:
        nxt = min(remaining, key=lambda p: road_km(here, p))
        remaining.remove(nxt)
        route.append(nxt)
        here = nxt
    return route + late


def route_distance(stops: list[dict], hotel: dict) -> float:
    if not stops:
        return 0.0
    path = [hotel, *stops, hotel]
    return sum(road_km(a, b) for a, b in zip(path, path[1:]))


def _route_cost(group: list[dict], hotel: dict) -> float:
    return route_distance(nearest_neighbour_route(group, hotel), hotel)


def improve_groups(groups: list[list[dict]], hotel: dict, max_passes: int = 4) -> list[list[dict]]:
    """Local search: swap stops between days whenever that shortens the total route."""
    groups = [list(g) for g in groups]
    costs = [_route_cost(g, hotel) for g in groups]
    for _ in range(max_passes):
        improved = False
        for a in range(len(groups)):
            for b in range(a + 1, len(groups)):
                for i in range(len(groups[a])):
                    for j in range(len(groups[b])):
                        ga, gb = list(groups[a]), list(groups[b])
                        ga[i], gb[j] = gb[j], ga[i]
                        ca, cb = _route_cost(ga, hotel), _route_cost(gb, hotel)
                        if ca + cb < costs[a] + costs[b] - 0.05:
                            groups[a], groups[b], costs[a], costs[b] = ga, gb, ca, cb
                            improved = True
        if not improved:
            break
    return groups


def _order_days(groups: list[list[dict]], hotel: dict) -> list[list[dict]]:
    """Chain non-empty days so consecutive days are in neighbouring areas."""
    filled = [g for g in groups if g]
    empty = [g for g in groups if not g]
    ordered, here = [], hotel
    while filled:
        nxt = min(filled, key=lambda g: road_km(here, centroid(g)))
        filled.remove(nxt)
        ordered.append(nxt)
        here = centroid(nxt)
    return ordered + empty


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------
def _free_time(anchor: dict, label: str = "Free time — explore the neighbourhood") -> dict:
    return {
        "id": f"free-{uuid.uuid4().hex[:8]}", "name": label, "category": "leisure",
        "lat": anchor["lat"], "lon": anchor["lon"], "cost": 0.0, "duration": 2.0,
        "tags": ["flexible"], "indoor": False, "generic": True,
        "description": "Unplanned time for cafés, a nap, or anything that caught your eye.",
    }


def _generic_meal(anchor: dict, profile: dict, prefs: dict, meal: str) -> dict:
    tier = BUDGET_TARGET_TIER.get(prefs.get("budget"), 2)
    costs = sorted(r["cost"] for r in profile["restaurants"] if r["tier"] == tier) or \
        sorted(r["cost"] for r in profile["restaurants"]) or [0.0]
    return {
        "id": f"meal-{uuid.uuid4().hex[:8]}", "name": f"{meal} at a local café nearby", "lat": anchor["lat"],
        "lon": anchor["lon"], "cost": costs[len(costs) // 2], "tier": tier, "cuisine": "Local",
        "tags": ["local"], "generic": True,
        "description": "No listed restaurant close by — ask locally or pack a meal for the excursion.",
    }


def pick_restaurant(anchor: dict, profile: dict, prefs: dict, used: set[str], *, dinner: bool,
                    want_tags: set[str] | None = None, exclude: set[str] | None = None) -> dict:
    tier_target = BUDGET_TARGET_TIER.get(prefs.get("budget"), 2)
    diet = (prefs.get("diet") or "").lower()
    nightlife = "Nightlife" in (prefs.get("interests") or [])
    exclude = exclude or set()
    best, best_score = None, float("-inf")
    for r in profile["restaurants"]:
        if r["id"] in exclude:
            continue
        dist = road_km(anchor, r)
        if dist > MEAL_SEARCH_RADIUS_KM:
            continue
        tags = set(r["tags"])
        s = -dist
        s -= 2.0 * abs(r["tier"] - tier_target)
        if diet == "vegetarian" and tags & {"vegetarian", "vegan"}:
            s += 9
        if diet == "vegan" and "vegan" in tags:
            s += 10
        if dinner and nightlife and "nightlife" in tags:
            s += 2
        if dinner and prefs.get("party") == "Couple" and "romantic" in tags:
            s += 1.5
        if want_tags:
            s += 6 * len(tags & want_tags)
        if r["id"] in used:
            s -= 6
        if s > best_score:
            best, best_score = r, s
    if best is None:
        return _generic_meal(anchor, profile, prefs, "Dinner" if dinner else "Lunch")
    return best


def _wants_evening(prefs: dict) -> bool:
    interests = prefs.get("interests") or []
    return (
        "Nightlife" in interests
        or "Culture" in interests
        or prefs.get("party") in {"Friends", "Couple"}
        or prefs.get("pace") == "Fast-Paced"
    )


def _slot(name: str, place: dict, kind: str) -> dict:
    return {"slot": name, "kind": kind, "place": place, "start": "", "end": "",
            "travel_km": 0.0, "travel_min": 0, "cost_local": 0.0}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def build_trip(profile: dict, prefs: dict, provider_label: str = "Demo mode (offline)", seed: int = 7) -> dict:
    """Generate a complete trip dictionary (see README › Data contracts)."""
    days = max(1, int(prefs.get("days", 3)))
    morning_n, afternoon_n = PACE_SLOTS.get(prefs.get("pace"), PACE_SLOTS["Moderate"])
    per_day = morning_n + afternoon_n
    hotel = profile["center"]

    day_pool = [p for p in profile["places"] if "evening" not in p.get("tags", [])]
    ranked = sorted(day_pool, key=lambda p: (-score_place(p, prefs, profile), p["name"]))

    # Long excursions get their own day, but only if they genuinely fit the traveller.
    max_full = days // 3
    full_day = [p for p in ranked if p["duration"] >= FULL_DAY_HOURS and score_place(p, prefs, profile) >= 4][:max_full]
    short = [p for p in ranked if p["duration"] < FULL_DAY_HOURS]
    cluster_days = days - len(full_day)
    chosen = short[: cluster_days * per_day]

    # Try several k-means seeds (plus the plain ranked split), keep the shortest, then refine.
    ranked_split = [chosen[i * per_day:(i + 1) * per_day] for i in range(cluster_days)]
    candidates = [balanced_clusters(chosen, cluster_days, seed=seed + i) for i in range(6)] + [ranked_split]
    best = min(candidates, key=lambda gs: sum(_route_cost(g, hotel) for g in gs))
    # Baseline for the "transit saved" metric: same stops and day structure, ranked order, no clustering.
    naive_km = sum(route_distance(d, hotel) for d in ranked_split + [[p] for p in full_day])
    groups = improve_groups(best, hotel) + [[p] for p in full_day]
    groups = _order_days(groups, hotel)


    trip = {
        "schema_version": SCHEMA_VERSION,
        "id": uuid.uuid4().hex[:12],
        "title": f"{profile['name']} · {days} day{'s' if days > 1 else ''}",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "provider": provider_label,
        "destination": {
            "name": profile["name"], "country": profile.get("country", ""), "currency": profile["currency"],
            "usd_per_unit": usd_per_unit(profile["currency"], profile.get("usd_per_unit")),
            "center": hotel, "emergency": profile.get("emergency", {}), "source": profile.get("source", "curated"),
        },
        "preferences": _serialisable_prefs(prefs),
        "profile": profile,
        "days": [],
        "summary": {},
    }

    used_restaurants: set[str] = set()
    used_evening: set[str] = set()
    for index, group in enumerate(groups):
        trip["days"].append(_assemble_day(index, group, profile, prefs, used_restaurants, used_evening))

    trip["summary"]["naive_route_km"] = round(naive_km, 1)
    recompute(trip)
    return trip


def _assemble_day(index: int, group: list[dict], profile: dict, prefs: dict,
                  used_restaurants: set[str], used_evening: set[str]) -> dict:
    morning_n, afternoon_n = PACE_SLOTS.get(prefs.get("pace"), PACE_SLOTS["Moderate"])
    hotel = profile["center"]
    anchor = centroid(group) if group else hotel
    slots: list[dict] = []

    if len(group) == 1 and group[0]["duration"] >= FULL_DAY_HOURS:
        excursion = group[0]
        slots.append(_slot(SLOT_MORNING, excursion, "activity"))
        lunch = pick_restaurant(excursion, profile, prefs, used_restaurants, dinner=False)
        used_restaurants.add(lunch["id"])
        slots.append(_slot(SLOT_LUNCH, lunch, "meal"))
        slots.append(_slot(SLOT_AFTERNOON, _free_time(hotel, "Return & unwind at the hotel"), "activity"))
        last = hotel
    else:
        route = nearest_neighbour_route(group, hotel)
        while len(route) < morning_n + afternoon_n:
            route.append(_free_time(route[-1] if route else anchor))
        morning, afternoon = route[:morning_n], route[morning_n:]
        for p in morning:
            slots.append(_slot(SLOT_MORNING, p, "activity"))
        lunch_anchor = centroid([morning[-1], afternoon[0]]) if afternoon else morning[-1]
        lunch = pick_restaurant(lunch_anchor, profile, prefs, used_restaurants, dinner=False)
        used_restaurants.add(lunch["id"])
        slots.append(_slot(SLOT_LUNCH, lunch, "meal"))
        for p in afternoon:
            slots.append(_slot(SLOT_AFTERNOON, p, "activity"))
        last = afternoon[-1] if afternoon else morning[-1]

    dinner = pick_restaurant(last, profile, prefs, used_restaurants, dinner=True)
    used_restaurants.add(dinner["id"])
    slots.append(_slot(SLOT_DINNER, dinner, "meal"))

    if _wants_evening(prefs):
        evening_pool = [p for p in profile["places"] if "evening" in p.get("tags", []) and p["id"] not in used_evening]
        if prefs.get("party") == "Family":
            evening_pool = [p for p in evening_pool if p["category"] != "nightlife"]
        if evening_pool:
            best = min(evening_pool, key=lambda p: road_km(dinner, p))
            if road_km(dinner, best) <= EVENING_SEARCH_RADIUS_KM:
                used_evening.add(best["id"])
                slots.append(_slot(SLOT_EVENING, best, "activity"))

    return {"day": index + 1, "date": "", "theme": "", "area": "", "slots": slots,
            "distance_km": 0.0, "costs": {}, "total_local": 0.0, "cumulative_local": 0.0, "tips": [],
            "focus": "Keep it balanced"}


def _serialisable_prefs(prefs: dict) -> dict:
    out = {}
    for key, value in prefs.items():
        out[key] = value.isoformat() if isinstance(value, date) else value
    return out


def recompute(trip: dict) -> dict:
    """Re-derive dates, times, distances, costs, themes and tips after any edit."""
    prefs = trip["preferences"]
    profile = trip["profile"]
    hotel = trip["destination"]["center"]
    currency = trip["destination"]["currency"]
    rate = trip["destination"]["usd_per_unit"]
    travellers = max(1, int(prefs.get("travellers", 1)))
    vehicles = -(-travellers // 4)
    rooms = -(-travellers // 2)
    nightly = profile["hotel"].get(prefs.get("budget"), profile["hotel"]["Moderate"]) * rooms
    nights = max(1, len(trip["days"]) - 1)

    try:
        start = date.fromisoformat(str(prefs.get("start_date")))
    except (TypeError, ValueError):
        start = date.today()

    cumulative = 0.0
    total_route = 0.0
    totals = {"stay": 0.0, "activities": 0.0, "food": 0.0, "transport": 0.0}
    for day in trip["days"]:
        day["date"] = (start + timedelta(days=day["day"] - 1)).isoformat()
        _schedule(day, prefs, hotel)
        activity_stops = [s["place"] for s in day["slots"]
                          if s["slot"] in (SLOT_MORNING, SLOT_AFTERNOON) and not s["place"].get("generic")]
        total_route += route_distance(activity_stops, hotel)

        costs = {"stay": nightly if day["day"] <= nights else 0.0, "activities": 0.0, "food": 0.0, "transport": 0.0}
        for s in day["slots"]:
            s["cost_local"] = round(s["place"].get("cost", 0.0) * travellers, 2)
            costs["food" if s["kind"] == "meal" else "activities"] += s["cost_local"]
        costs["transport"] = round(day["distance_km"] * profile["transport_per_km"] * vehicles, 2)
        day["costs"] = {k: round(v, 2) for k, v in costs.items()}
        day["total_local"] = round(sum(costs.values()), 2)
        cumulative += day["total_local"]
        day["cumulative_local"] = round(cumulative, 2)
        for k in totals:
            totals[k] += costs[k]
        day["theme"], day["area"] = _theme(day)
        day["tips"] = _tips(day, profile, prefs)

    total = sum(totals.values())
    naive = trip["summary"].get("naive_route_km", total_route)
    saved = max(0.0, naive - total_route)
    trip["summary"].update({
        "total_local": round(total, 2),
        "total_inr": round(convert(total, currency, "INR", rate), 0),
        "total_usd": round(convert(total, currency, "USD", rate), 0),
        "per_person_inr": round(convert(total, currency, "INR", rate) / travellers, 0),
        "by_category": {k: round(v, 2) for k, v in totals.items()},
        "distance_km": round(sum(d["distance_km"] for d in trip["days"]), 1),
        "route_km": round(total_route, 1),
        "naive_route_km": round(naive, 1),
        "transit_saved_km": round(saved, 1),
        "transit_saved_pct": round(100 * saved / naive, 0) if naive else 0.0,
        "activities": sum(1 for d in trip["days"] for s in d["slots"] if s["kind"] == "activity" and not s["place"].get("generic")),
        "travellers": travellers,
        "nights": nights,
    })
    budget_cap = float(prefs.get("budget_cap_inr") or 0)
    trip["summary"]["budget_cap_inr"] = budget_cap
    trip["summary"]["over_budget"] = bool(budget_cap and trip["summary"]["total_inr"] > budget_cap)
    return trip


def _schedule(day: dict, prefs: dict, hotel: dict) -> None:
    clock = PACE_START_HOUR.get(prefs.get("pace"), 9.0)
    here = hotel
    distance = 0.0
    for s in day["slots"]:
        place = s["place"]
        km = road_km(here, place)
        travel_h = round_minutes(km / CITY_SPEED_KMH) if km > 0.3 else 0.0
        s["travel_km"] = round(km, 1)
        s["travel_min"] = int(round(travel_h * 60))
        distance += km
        clock += travel_h
        if s["slot"] == SLOT_LUNCH:
            clock = max(clock, LUNCH_EARLIEST)
            duration = LUNCH_DURATION
        elif s["slot"] == SLOT_DINNER:
            clock = max(clock, DINNER_EARLIEST)
            duration = DINNER_DURATION
        elif s["slot"] == SLOT_EVENING:
            duration = min(place.get("duration", EVENING_DURATION), 2.5)
        else:
            duration = place.get("duration", 1.5)
        s["start"], s["end"] = fmt_hour(clock), fmt_hour(clock + duration)
        clock += duration
        here = place
    distance += road_km(here, hotel)
    day["distance_km"] = round(distance, 1)


_CATEGORY_THEMES = {
    "history": "Heritage & History", "culture": "Art & Culture", "nature": "Nature & Views",
    "adventure": "Adventure", "beach": "Sun & Sand", "shopping": "Markets & Shopping",
    "nightlife": "After Dark", "food": "Food Trail", "wellness": "Rest & Wellness", "landmark": "Icons & Landmarks",
}


def _theme(day: dict) -> tuple[str, str]:
    acts = [s["place"] for s in day["slots"] if s["kind"] == "activity" and not s["place"].get("generic")]
    if not acts:
        return "Slow day", "Around your hotel"
    counts: dict[str, int] = {}
    for p in acts:
        counts[p["category"]] = counts.get(p["category"], 0) + 1
    top = sorted(counts, key=lambda c: (-counts[c], c))[:2]
    theme = " + ".join(_CATEGORY_THEMES.get(c, c.title()) for c in top)
    if any(p["duration"] >= FULL_DAY_HOURS for p in acts):
        theme = "Full-day excursion"
    area_anchor = min(acts, key=lambda p: road_km(p, centroid(acts)))
    return theme, f"Around {area_anchor['name']}"


def _tips(day: dict, profile: dict, prefs: dict) -> list[str]:
    tips = []
    places = [s["place"] for s in day["slots"]]
    tags = {t for p in places for t in p.get("tags", [])}
    month = date.fromisoformat(day["date"]).month
    if month in profile.get("avoid_months", {}):
        tips.append(f"Season alert: {profile['avoid_months'][month]} — keep an indoor backup handy.")
    if tags & {"temple", "church"}:
        tips.append("Dress modestly (shoulders & knees covered) for religious sites.")
    if tags & {"adventure", "watersports", "trek"}:
        tips.append("Pre-book adventure activities and carry a photo ID.")
    if "sunset" in tags:
        tips.append("Time your last stop for golden hour — arrive 30 min before sunset.")
    if day["distance_km"] > 60:
        tips.append("Long transfer today — start early and carry water and snacks.")
    if any(p.get("duration", 0) >= FULL_DAY_HOURS for p in places):
        tips.append("Full-day excursion: book transport the evening before.")
    if (prefs.get("diet") or "").lower() in {"vegetarian", "vegan"}:
        meals = [s["place"] for s in day["slots"] if s["kind"] == "meal"]
        if any(not (set(m.get("tags", [])) & {"vegetarian", "vegan"}) for m in meals):
            tips.append(f"Ask for {prefs['diet'].lower()} options at meals not tagged veg-friendly.")
    if not tips:
        tips.append("Keep small change for tips, water and local transport.")
    return tips[:4]


# ---------------------------------------------------------------------------
# Edits: swap a slot, regenerate a day
# ---------------------------------------------------------------------------
SWAP_KEYWORDS = {
    "museum": ({"culture", "history"}, {"museum"}),
    "history": ({"history"}, {"heritage"}),
    "heritage": ({"history"}, {"heritage"}),
    "temple": ({"culture"}, {"temple"}),
    "art": ({"culture"}, {"art"}),
    "outdoor": ({"nature", "beach", "adventure"}, set()),
    "nature": ({"nature"}, {"park", "garden", "views"}),
    "park": ({"nature"}, {"park", "garden"}),
    "garden": ({"nature"}, {"garden"}),
    "view": (set(), {"views"}),
    "sunset": (set(), {"sunset"}),
    "beach": ({"beach"}, set()),
    "market": ({"shopping", "food"}, {"market"}),
    "shop": ({"shopping"}, {"market", "souvenirs"}),
    "food": ({"food"}, {"street-food", "market"}),
    "street": (set(), {"street-food"}),
    "adventure": ({"adventure"}, {"adventure"}),
    "trek": ({"adventure", "nature"}, {"trek"}),
    "hike": ({"adventure", "nature"}, {"trek"}),
    "water": (set(), {"watersports"}),
    "spa": ({"wellness"}, {"spa"}),
    "relax": ({"wellness", "beach", "nature"}, {"spa"}),
    "nightlife": ({"nightlife"}, {"nightlife", "bar"}),
    "bar": ({"nightlife"}, {"bar", "nightlife"}),
    "party": ({"nightlife"}, {"nightlife"}),
    "kid": (set(), {"family"}),
    "family": (set(), {"family"}),
    "romantic": (set(), {"romantic", "sunset"}),
    "landmark": ({"landmark"}, {"iconic"}),
    "famous": (set(), {"iconic"}),
    "vegetarian": (set(), {"vegetarian", "vegan"}),
    "veg": (set(), {"vegetarian", "vegan"}),
    "vegan": (set(), {"vegan"}),
    "seafood": (set(), {"seafood"}),
    "local": (set(), {"local"}),
    "fancy": (set(), {"luxury", "romantic"}),
    "luxury": (set(), {"luxury"}),
}
INDOOR_WORDS = {"indoor", "rain", "inside"}
CHEAP_WORDS = {"cheap", "budget", "free", "affordable"}


def parse_instruction(text: str) -> dict:
    """Turn 'Swap museum for outdoor market' into desired categories/tags.

    Only the part after 'for'/'with'/'to'/'into' describes what the traveller wants.
    """
    lowered = f" {text.lower()} "
    for sep in (" for ", " with ", " into ", " to "):
        if sep in lowered:
            lowered = lowered.split(sep, 1)[1]
            break
    words = lowered.replace(",", " ").replace("-", " ").split()
    cats, tags = set(), set()
    for word in words:
        for key, (c, t) in SWAP_KEYWORDS.items():
            if word.startswith(key):
                cats |= c
                tags |= t
    return {
        "categories": cats,
        "tags": tags,
        "indoor": bool(INDOOR_WORDS & set(words)),
        "outdoor": "outdoor" in words or "outside" in words,
        "cheap": bool(CHEAP_WORDS & set(words)),
    }


def used_ids(trip: dict) -> set[str]:
    return {s["place"]["id"] for d in trip["days"] for s in d["slots"]}


def find_replacement(trip: dict, day_idx: int, slot_idx: int, instruction: str) -> tuple[dict | None, bool, tuple | None]:
    """Offline swap. Returns (replacement, matched_request, origin).

    ``origin`` is ``(day_idx, slot_idx)`` when every suitable attraction is already
    planned and the best match is borrowed from another day (the two stops trade places).
    """
    day = trip["days"][day_idx]
    slot = day["slots"][slot_idx]
    profile, prefs = trip["profile"], trip["preferences"]
    want = parse_instruction(instruction)
    taken = used_ids(trip)
    is_meal = slot["kind"] == "meal"
    evening = slot["slot"] == SLOT_EVENING
    others = [s["place"] for i, s in enumerate(day["slots"]) if i != slot_idx and not s["place"].get("generic")]
    anchor = centroid(others) if others else slot["place"]

    candidates: list[tuple[dict, tuple | None]]
    if is_meal:
        pool = [r for r in profile["restaurants"] if r["id"] not in taken] or \
            [r for r in profile["restaurants"] if r["id"] != slot["place"]["id"]]
        candidates = [(r, None) for r in pool]
    else:
        candidates = [(p, None) for p in profile["places"] if p["id"] not in taken
                      and ("evening" in p.get("tags", [])) == evening and p["duration"] < FULL_DAY_HOURS]
        if not candidates and slot["place"].get("duration", 0) < FULL_DAY_HOURS:
            for di, other_day in enumerate(trip["days"]):
                if di == day_idx:
                    continue
                for si, other in enumerate(other_day["slots"]):
                    p = other["place"]
                    if (other["kind"] == "activity" and not p.get("generic") and p["duration"] < FULL_DAY_HOURS
                            and (other["slot"] == SLOT_EVENING) == evening):
                        candidates.append((p, (di, si)))
    if not candidates:
        return None, False, None

    def match(c: dict) -> int:
        hit = len(set(c.get("tags", [])) & want["tags"]) * 2
        hit += 3 if c.get("category") in want["categories"] else 0
        if want["indoor"] and c.get("indoor"):
            hit += 2
        if want["outdoor"] and not c.get("indoor", True):
            hit += 1
        if want["cheap"] and c.get("cost", 0) <= slot["place"].get("cost", 0):
            hit += 1
        return hit

    def score(item: tuple[dict, tuple | None]) -> float:
        c = item[0]
        base = 0.0 if is_meal else score_place(c, prefs, profile) * 0.3
        return match(c) * 4 + base - road_km(anchor, c) * 0.35

    best, origin = max(candidates, key=score)
    return best, match(best) > 0, origin


def exchange_slots(trip: dict, a: tuple[int, int], b: tuple[int, int]) -> dict:
    """Trade the places in two slots (used when the attraction pool is exhausted)."""
    slot_a = trip["days"][a[0]]["slots"][a[1]]
    slot_b = trip["days"][b[0]]["slots"][b[1]]
    slot_a["place"], slot_b["place"] = slot_b["place"], slot_a["place"]
    return recompute(trip)


def apply_swap(trip: dict, day_idx: int, slot_idx: int, new_place: dict) -> dict:
    trip["days"][day_idx]["slots"][slot_idx]["place"] = new_place
    if new_place["id"] not in {p["id"] for p in trip["profile"]["places"] + trip["profile"]["restaurants"]}:
        bucket = "restaurants" if "tier" in new_place else "places"
        trip["profile"][bucket].append(new_place)
    return recompute(trip)


def regenerate_day(trip: dict, day_idx: int, focus: str = "Keep it balanced", seed: int | None = None) -> dict:
    """Rebuild one day from unused attractions near the same area, leaving other days untouched."""
    profile, prefs = trip["profile"], trip["preferences"]
    day = trip["days"][day_idx]
    rng = random.Random(seed)
    current = [s["place"] for s in day["slots"] if s["kind"] == "activity" and s["slot"] != SLOT_EVENING]
    anchor = centroid([p for p in current if not p.get("generic")] or current) if current else profile["center"]
    taken_elsewhere = {s["place"]["id"] for i, d in enumerate(trip["days"]) if i != day_idx for s in d["slots"]}
    current_ids = {p["id"] for p in current}
    morning_n, afternoon_n = PACE_SLOTS.get(prefs.get("pace"), PACE_SLOTS["Moderate"])
    need = morning_n + afternoon_n

    pool = [p for p in profile["places"] if p["id"] not in taken_elsewhere
            and "evening" not in p.get("tags", []) and p["duration"] < FULL_DAY_HOURS]

    def score(p: dict) -> float:
        s = score_place(p, prefs, profile, focus) - road_km(anchor, p) * 0.25
        s -= 2.5 if p["id"] in current_ids else 0.0  # prefer fresh ideas
        return s + rng.uniform(0, 1.2)

    picks = sorted(pool, key=score, reverse=True)[:need]
    used_r = {s["place"]["id"] for i, d in enumerate(trip["days"]) if i != day_idx for s in d["slots"] if s["kind"] == "meal"}
    used_e = {s["place"]["id"] for i, d in enumerate(trip["days"]) if i != day_idx for s in d["slots"] if s["slot"] == SLOT_EVENING}
    new_day = _assemble_day(day_idx, picks, profile, prefs, used_r, used_e)
    new_day["focus"] = focus
    trip["days"][day_idx] = new_day
    return recompute(trip)


def snapshot(trip: dict) -> dict:
    return copy.deepcopy(trip)


def public_view(trip: dict) -> dict:
    """Trip without the bulky destination profile — used for JSON export."""
    return {k: v for k, v in trip.items() if k != "profile"}


def ai_replacement(trip: dict, day_idx: int, slot_idx: int, instruction: str, client) -> dict:
    """Ask the configured LLM for a replacement; raises ``LLMError``/``ValueError`` on failure."""
    from .prompts import SYSTEM_TRAVEL_EXPERT, swap_prompt
    from .schemas import validate_place, validate_restaurant

    day = trip["days"][day_idx]
    slot = day["slots"][slot_idx]
    is_meal = slot["kind"] == "meal"
    others = [s["place"] for i, s in enumerate(day["slots"]) if i != slot_idx and not s["place"].get("generic")]
    near = centroid(others) if others else slot["place"]
    prompt = swap_prompt(
        trip["destination"]["name"], instruction, slot["slot"], slot["place"],
        [p["name"] for p in others], near, trip["preferences"], is_meal,
    )
    raw = client.generate_json(SYSTEM_TRAVEL_EXPERT, prompt, 0.5)
    raw = raw.get("place", raw) if isinstance(raw, dict) else raw
    validator = validate_restaurant if is_meal else validate_place
    place = validator(raw, trip["destination"]["center"], max_km=80, city=trip["destination"]["name"])
    if not place:
        raise ValueError("The AI suggestion had no valid name or coordinates.")
    if place["id"] in used_ids(trip):
        raise ValueError(f"{place['name']} is already in your plan.")
    return place
