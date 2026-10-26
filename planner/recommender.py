"""Smart destination recommender and destination-profile resolution."""

from __future__ import annotations

import calendar
from datetime import date

from . import data
from .config import BUDGET_TARGET_TIER
from .llm import LLMClient, LLMError
from .prompts import SYSTEM_TRAVEL_EXPERT, destination_profile_prompt, recommendation_prompt
from .schemas import validate_profile, validate_recommendations
from .utils import convert, usd_per_unit


def _travel_month(prefs: dict) -> int:
    start = prefs.get("start_date")
    if isinstance(start, date):
        return start.month
    try:
        return date.fromisoformat(str(start)).month
    except (TypeError, ValueError):
        return date.today().month


def estimate_daily_cost_inr(profile: dict, budget: str, travellers: int = 1) -> float:
    """Per-person daily cost (stay share + 2 meals + ~2 paid activities + local rides) in INR."""
    travellers = max(1, travellers)
    tier = BUDGET_TARGET_TIER.get(budget, 2)
    rooms = max(1, -(-travellers // 2))
    stay = profile["hotel"].get(budget, profile["hotel"]["Moderate"]) * rooms / travellers
    meals = sorted(r["cost"] for r in profile["restaurants"] if abs(r["tier"] - tier) <= 1) or [r["cost"] for r in profile["restaurants"]]
    meal = meals[len(meals) // 2] if meals else 0
    paid = sorted(p["cost"] for p in profile["places"] if p["cost"] > 0)
    activity = paid[len(paid) // 2] if paid else 0
    rides = profile["transport_per_km"] * 15 / max(1, travellers / 2)
    local_total = stay + 2 * meal + 1.5 * activity + rides
    return convert(local_total, profile["currency"], "INR", usd_per_unit(profile["currency"], profile.get("usd_per_unit")))


def score_destination(profile: dict, prefs: dict) -> tuple[float, list[str]]:
    """Return (score 0-100, human-readable reasons) for a curated destination."""
    reasons: list[str] = []
    score = 40.0
    vibe = prefs.get("vibe") or "Any"
    if vibe != "Any":
        if vibe in profile["vibes"]:
            score += 25
            reasons.append(f"Strong match for a {vibe.lower()} vibe")
        else:
            score -= 12

    month = _travel_month(prefs)
    month_name = calendar.month_name[month]
    if month in profile["best_months"]:
        score += 15
        reasons.append(f"{month_name} is peak season")
    elif month in profile["avoid_months"]:
        score -= 20
        reasons.append(f"Heads-up: {profile['avoid_months'][month].lower()} in {month_name}")
    else:
        score += 3

    budget = prefs.get("budget", "Moderate")
    tier_gap = profile["cost_tier"] - BUDGET_TARGET_TIER.get(budget, 2)
    if tier_gap <= 0:
        score += 10 if tier_gap == 0 else 6
        reasons.append(f"Fits a {budget.lower()} budget")
    else:
        score -= 10 * tier_gap

    interests = prefs.get("interests") or []
    overlap = [i for i in interests if i in profile["interests"]]
    if interests:
        score += 15 * len(overlap) / len(interests)
        if overlap:
            reasons.append("Great for " + ", ".join(i.lower() for i in overlap[:3]))

    party = prefs.get("party")
    if party in profile["good_for"]:
        score += 5
        if profile["good_for"].index(party) == 0:
            reasons.append(f"Especially loved by {party.lower()} travellers")

    region = prefs.get("region", "Anywhere")
    is_india = profile["country"] == "India"
    if (region == "India only" and not is_india) or (region == "International only" and is_india):
        score -= 100

    return max(0.0, min(100.0, score)), reasons


def recommend_offline(prefs: dict, top_n: int = 3) -> list[dict]:
    results = []
    for name in data.list_destinations():
        profile = data.DESTINATIONS[name]
        score, reasons = score_destination(profile, prefs)
        if score <= 0:
            continue
        month = _travel_month(prefs)
        season_note = (
            "Peak season" if month in profile["best_months"]
            else profile["avoid_months"].get(month, "Shoulder season — fewer crowds")
        )
        results.append({
            "city": name,
            "country": profile["country"],
            "match_score": int(round(score)),
            "highlights": profile["highlights"][:4],
            "why": ". ".join(reasons[:3]) + "." if reasons else "A solid all-round choice.",
            "season_note": season_note,
            "est_daily_cost_inr": round(estimate_daily_cost_inr(profile, prefs.get("budget", "Moderate"),
                                                                prefs.get("travellers", 1)), -1),
            "curated": True,
        })
    results.sort(key=lambda r: (-r["match_score"], r["city"]))
    return results[:top_n]


def recommend(prefs: dict, client: LLMClient | None) -> tuple[list[dict], str | None]:
    """AI recommendations when a provider is configured; offline scoring otherwise.

    Returns (recommendations, warning-or-None).
    """
    if client and client.enabled:
        try:
            month_name = calendar.month_name[_travel_month(prefs)]
            raw = client.generate_json(SYSTEM_TRAVEL_EXPERT, recommendation_prompt(prefs, month_name), 0.6)
            recs = validate_recommendations(raw)
            for rec in recs:
                rec["curated"] = data.get_destination(rec["city"]) is not None
            return recs, None
        except (LLMError, ValueError) as exc:
            return recommend_offline(prefs), f"AI recommendations unavailable ({exc}). Showing offline picks."
    return recommend_offline(prefs), None


def resolve_profile(city: str, prefs: dict, client: LLMClient | None) -> tuple[dict, str | None]:
    """Return a destination profile for ``city`` plus an optional warning.

    Order: AI profile (if a provider is configured) -> curated knowledge base -> generic template.
    """
    curated = data.get_destination(city)
    warning = None
    if client and client.enabled:
        try:
            raw = client.generate_json(SYSTEM_TRAVEL_EXPERT, destination_profile_prompt(city, prefs), 0.3)
            profile = validate_profile(raw, city)
            if curated:  # keep curated metadata the recommender relies on
                for key in ("vibes", "cost_tier", "good_for", "interests"):
                    profile[key] = curated[key]
            return profile, None
        except (LLMError, ValueError) as exc:
            warning = f"AI planning failed ({exc}). Used offline data instead."
    if curated:
        return curated, warning
    generic = data.generic_destination(city)
    note = (
        f"'{city.strip()}' isn't in the offline guide, so this is a template plan with placeholder venues. "
        "Add a Gemini or Groq API key in the sidebar for real places."
    )
    return generic, f"{warning} {note}" if warning else note
