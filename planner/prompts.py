"""Prompt templates. Each prompt embeds its JSON contract so replies stay machine-readable."""

from __future__ import annotations

import json

from .schemas import PLACE_CONTRACT, PROFILE_CONTRACT, RECOMMENDATION_CONTRACT, RESTAURANT_CONTRACT

SYSTEM_TRAVEL_EXPERT = (
    "You are a meticulous travel-planning engine for a trip-planning web app. "
    "You only answer with a single JSON object that matches the requested contract exactly. "
    "Use real, currently operating places with accurate WGS84 coordinates and realistic prices "
    "in the local currency. Use English names. Never include markdown, comments or extra keys."
)


def _prefs_summary(prefs: dict) -> str:
    return json.dumps({
        "vibe": prefs.get("vibe"),
        "trip_days": prefs.get("days"),
        "start_date": prefs.get("start_date"),
        "budget_level": prefs.get("budget"),
        "party": prefs.get("party"),
        "travellers": prefs.get("travellers"),
        "pace": prefs.get("pace"),
        "interests": prefs.get("interests"),
        "diet": prefs.get("diet"),
        "region_preference": prefs.get("region"),
    }, ensure_ascii=False)


def destination_profile_prompt(city: str, prefs: dict) -> str:
    n_places = min(24, max(12, int(prefs.get("days", 3)) * 4))
    return (
        f"Build a destination profile for: {city}.\n"
        f"Traveller preferences: {_prefs_summary(prefs)}\n\n"
        f"Requirements:\n"
        f"- {n_places} attractions spread across different neighbourhoods, biased towards the traveller's interests,"
        f" including the must-see landmarks. Tag after-dark activities with 'evening'.\n"
        f"- 8 restaurants covering cheap, mid-range and upscale options; tag vegetarian/vegan-friendly ones.\n"
        f"- All coordinates must be within 60 km of the city centre unless it is a famous day trip.\n"
        f"- Prices are per person in the local currency.\n\n"
        f"Return JSON matching this contract:\n{json.dumps(PROFILE_CONTRACT, indent=1)}"
    )


def recommendation_prompt(prefs: dict, month_name: str) -> str:
    return (
        "Recommend the top 3 destinations for this traveller who has not chosen a destination yet.\n"
        f"Traveller preferences: {_prefs_summary(prefs)}\n"
        f"Travel month: {month_name}. Prices in Indian Rupees (INR) for the cost estimate.\n"
        "Rank by fit with the vibe, the weather in that month, the budget level and the interests. "
        "Respect the region preference.\n\n"
        f"Return JSON matching this contract:\n{json.dumps(RECOMMENDATION_CONTRACT, indent=1)}"
    )


def swap_prompt(city: str, instruction: str, slot_name: str, current: dict, day_places: list[str],
                near: dict, prefs: dict, is_meal: bool) -> str:
    contract = RESTAURANT_CONTRACT if is_meal else PLACE_CONTRACT
    kind = "restaurant" if is_meal else "attraction or activity"
    return (
        f"City: {city}. The traveller wants to replace one {kind} in their itinerary.\n"
        f"Time slot: {slot_name}. Currently planned: {current.get('name')} ({current.get('category', current.get('cuisine', ''))}).\n"
        f"Request: \"{instruction}\".\n"
        f"Other stops that day: {', '.join(day_places) or 'none'}.\n"
        f"Stay close to latitude {near['lat']:.4f}, longitude {near['lon']:.4f} (within ~8 km) to avoid backtracking.\n"
        f"Traveller preferences: {_prefs_summary(prefs)}\n"
        "Suggest ONE real alternative that is not already in the plan.\n\n"
        f"Return JSON with a single key \"place\" whose value matches:\n{json.dumps(contract, indent=1)}"
    )
