"""JSON data contracts shared by the AI layer, the itinerary engine, storage and exports.

LLM output is never trusted blindly: every response goes through a ``validate_*``
function that coerces types, clamps values and drops malformed items, so the UI
always renders predictable structures.
"""

from __future__ import annotations

import re
from typing import Any

from .config import USD_PER_UNIT
from .utils import haversine_km

PLACE_CATEGORIES = {
    "history", "culture", "nature", "adventure", "beach", "shopping",
    "nightlife", "food", "wellness", "landmark",
}

# Example-shaped contracts embedded into prompts so the model mirrors them.
PLACE_CONTRACT = {
    "name": "string (English)",
    "category": "one of: " + ", ".join(sorted(PLACE_CATEGORIES)),
    "lat": "number (WGS84 latitude)",
    "lon": "number (WGS84 longitude)",
    "cost": "number, typical entry/activity price per person in local currency (0 if free)",
    "duration": "number, typical visit length in hours",
    "tags": ["short lowercase tags e.g. iconic, heritage, views, sunset, family, market, temple, evening, spa"],
    "indoor": "boolean",
    "description": "one sentence",
}
RESTAURANT_CONTRACT = {
    "name": "string (English)",
    "lat": "number",
    "lon": "number",
    "cost": "number, average meal price per person in local currency",
    "tier": "integer 1 (cheap) | 2 (mid-range) | 3 (upscale)",
    "cuisine": "string",
    "tags": ["e.g. local, vegetarian, vegan, seafood, nightlife, romantic, street-food, views"],
    "description": "one sentence",
}
PROFILE_CONTRACT = {
    "name": "city name",
    "country": "country name",
    "currency": "ISO 4217 code of the local currency",
    "usd_per_unit": "number, approximate USD value of 1 unit of local currency",
    "center": {"lat": "number", "lon": "number"},
    "best_months": ["integers 1-12"],
    "avoid_months": {"month number as string": "short reason"},
    "highlights": ["3-5 short strings"],
    "hotel": {"Budget": "number per room-night, local currency", "Moderate": "number", "Luxury": "number"},
    "transport_per_km": "number, taxi/ride-hail cost per km in local currency",
    "emergency": {"service name": "phone number"},
    "places": [PLACE_CONTRACT],
    "restaurants": [RESTAURANT_CONTRACT],
}
RECOMMENDATION_CONTRACT = {
    "recommendations": [
        {
            "city": "string",
            "country": "string",
            "match_score": "integer 0-100",
            "highlights": ["3-4 short tags"],
            "why": "one or two sentences tailored to the traveller",
            "season_note": "short weather note for the travel month",
            "est_daily_cost_inr": "number, per person per day incl. stay at the chosen budget level",
        }
    ]
}


def _num(value: Any, default: float | None = None) -> float | None:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"-?\d+(?:[.,]\d+)?", value.replace(",", ""))
        if match:
            try:
                return float(match.group(0))
            except ValueError:
                return default
    return default


def _text(value: Any, default: str = "", limit: int = 240) -> str:
    if value is None:
        return default
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text[:limit] if text else default


def _tags(value: Any) -> list[str]:
    if isinstance(value, str):
        value = re.split(r"[,\s]+", value)
    if not isinstance(value, list):
        return []
    out = []
    for tag in value:
        tag = _text(tag, limit=30).lower().replace(" ", "-")
        if tag and tag not in out:
            out.append(tag)
    return out[:10]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _coords_ok(lat: float | None, lon: float | None, center: dict | None, max_km: float) -> bool:
    if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return False
    if center:
        return haversine_km(lat, lon, center["lat"], center["lon"]) <= max_km
    return True


def validate_place(raw: Any, center: dict | None = None, max_km: float = 150.0, city: str = "") -> dict | None:
    if not isinstance(raw, dict):
        return None
    name = _text(raw.get("name"), limit=90)
    lat, lon = _num(raw.get("lat")), _num(raw.get("lon"))
    if not name or not _coords_ok(lat, lon, center, max_km):
        return None
    category = _text(raw.get("category"), "landmark").lower()
    if category not in PLACE_CATEGORIES:
        category = "landmark"
    return {
        "id": _slug(f"{city}-{name}"),
        "name": name,
        "category": category,
        "lat": lat,
        "lon": lon,
        "cost": max(0.0, _num(raw.get("cost"), 0.0)),
        "duration": min(10.0, max(0.5, _num(raw.get("duration"), 1.5))),
        "tags": _tags(raw.get("tags")),
        "indoor": bool(raw.get("indoor", False)),
        "description": _text(raw.get("description"), limit=200),
        "generic": False,
    }


def validate_restaurant(raw: Any, center: dict | None = None, max_km: float = 150.0, city: str = "") -> dict | None:
    if not isinstance(raw, dict):
        return None
    name = _text(raw.get("name"), limit=90)
    lat, lon = _num(raw.get("lat")), _num(raw.get("lon"))
    if not name or not _coords_ok(lat, lon, center, max_km):
        return None
    tier = int(_num(raw.get("tier"), 2) or 2)
    return {
        "id": _slug(f"{city}-{name}"),
        "name": name,
        "lat": lat,
        "lon": lon,
        "cost": max(0.0, _num(raw.get("cost"), 0.0)),
        "tier": min(3, max(1, tier)),
        "cuisine": _text(raw.get("cuisine"), "Local", limit=60),
        "tags": _tags(raw.get("tags")),
        "description": _text(raw.get("description"), limit=200),
        "generic": False,
    }


def validate_profile(raw: Any, requested_name: str) -> dict:
    """Coerce an AI destination profile; raise ``ValueError`` if it is unusable."""
    if not isinstance(raw, dict):
        raise ValueError("Destination profile is not a JSON object.")
    center_raw = raw.get("center") or {}
    lat, lon = _num(center_raw.get("lat")), _num(center_raw.get("lon"))
    if not _coords_ok(lat, lon, None, 0):
        raise ValueError("Destination profile is missing valid centre coordinates.")
    center = {"lat": lat, "lon": lon}
    city = _text(raw.get("name"), requested_name, limit=60)

    places = [p for p in (validate_place(x, center, city=city) for x in raw.get("places") or []) if p]
    restaurants = [r for r in (validate_restaurant(x, center, city=city) for x in raw.get("restaurants") or []) if r]
    places = list({p["id"]: p for p in places}.values())
    restaurants = list({r["id"]: r for r in restaurants}.values())
    if len(places) < 4:
        raise ValueError("The AI returned too few valid attractions to plan a trip.")
    if not restaurants:
        raise ValueError("The AI returned no valid restaurants.")

    currency = _text(raw.get("currency"), "USD", limit=3).upper()
    rate = _num(raw.get("usd_per_unit"))
    if currency in USD_PER_UNIT:
        rate = USD_PER_UNIT[currency]
    elif not rate or rate <= 0:
        currency, rate = "USD", 1.0

    hotel_raw = raw.get("hotel") or {}
    hotel = {}
    for level, usd_default in (("Budget", 45), ("Moderate", 110), ("Luxury", 320)):
        hotel[level] = _num(hotel_raw.get(level)) or round(usd_default / rate)

    avoid = {}
    for key, reason in (raw.get("avoid_months") or {}).items():
        month = _num(key)
        if month and 1 <= month <= 12:
            avoid[int(month)] = _text(reason, "Off-season", limit=60)
    best = sorted({int(m) for m in (_num(x) for x in raw.get("best_months") or []) if m and 1 <= m <= 12})

    emergency = {
        _text(k, limit=40): _text(v, limit=40)
        for k, v in (raw.get("emergency") or {}).items() if _text(k) and _text(v)
    } or {"General emergency": "112"}

    return {
        "name": city,
        "country": _text(raw.get("country"), limit=60),
        "currency": currency,
        "usd_per_unit": rate,
        "center": center,
        "vibes": [], "cost_tier": 2, "good_for": [],
        "best_months": best,
        "avoid_months": avoid,
        "interests": [],
        "highlights": [_text(h, limit=40) for h in (raw.get("highlights") or [])][:5],
        "hotel": hotel,
        "transport_per_km": _num(raw.get("transport_per_km")) or round(1.2 / rate, 2),
        "emergency": emergency,
        "places": places,
        "restaurants": restaurants,
        "source": "ai",
    }


def validate_recommendations(raw: Any) -> list[dict]:
    items = raw.get("recommendations") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        raise ValueError("Recommendations are not a list.")
    out = []
    for item in items:
        if not isinstance(item, dict) or not _text(item.get("city")):
            continue
        out.append({
            "city": _text(item.get("city"), limit=60),
            "country": _text(item.get("country"), limit=60),
            "match_score": int(min(100, max(0, _num(item.get("match_score"), 70)))),
            "highlights": [_text(h, limit=40) for h in (item.get("highlights") or [])][:4],
            "why": _text(item.get("why"), limit=400),
            "season_note": _text(item.get("season_note"), limit=120),
            "est_daily_cost_inr": max(0.0, _num(item.get("est_daily_cost_inr"), 0.0)),
            "curated": False,
        })
    if not out:
        raise ValueError("No usable recommendations returned.")
    return out[:3]
