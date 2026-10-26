"""Small shared helpers: geography, money formatting and time formatting."""

from __future__ import annotations

import math

from .config import CURRENCY_SYMBOLS, ROAD_FACTOR, USD_PER_UNIT

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def road_km(a: dict, b: dict) -> float:
    """Approximate road distance between two objects that carry lat/lon keys."""
    return haversine_km(a["lat"], a["lon"], b["lat"], b["lon"]) * ROAD_FACTOR


def centroid(points: list[dict]) -> dict:
    if not points:
        return {"lat": 0.0, "lon": 0.0}
    return {
        "lat": sum(p["lat"] for p in points) / len(points),
        "lon": sum(p["lon"] for p in points) / len(points),
    }


# ---------------------------------------------------------------------------
# Money
# ---------------------------------------------------------------------------
def usd_per_unit(currency: str, fallback: float | None = None) -> float:
    if currency in USD_PER_UNIT:
        return USD_PER_UNIT[currency]
    return fallback if fallback and fallback > 0 else 1.0


def convert(amount: float, from_ccy: str, to_ccy: str, from_rate: float | None = None) -> float:
    """Convert using the indicative USD cross-rates in config."""
    usd = amount * usd_per_unit(from_ccy, from_rate)
    return usd / usd_per_unit(to_ccy)


def symbol(currency: str) -> str:
    return CURRENCY_SYMBOLS.get(currency, f"{currency} ")


def fmt_money(amount: float, currency: str, ascii_only: bool = False) -> str:
    """Human-friendly money string. ``ascii_only`` uses ISO codes (for PDF fonts)."""
    amount = float(amount or 0)
    if currency == "INR" and not ascii_only:
        return f"₹{_indian_grouping(round(amount))}"
    text = f"{round(amount):,}"
    if ascii_only:
        return f"{currency} {text}"
    return f"{symbol(currency)}{text}"


def _indian_grouping(n: int) -> str:
    """Format 1234567 as 12,34,567 (lakh/crore grouping)."""
    sign = "-" if n < 0 else ""
    s = str(abs(int(n)))
    if len(s) <= 3:
        return sign + s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return sign + ",".join(parts) + "," + tail


# ---------------------------------------------------------------------------
# Time
# ---------------------------------------------------------------------------
def fmt_hour(hour: float) -> str:
    """12.75 -> '12:45'. Rounds to the nearest 5 minutes."""
    total = int(round(hour * 60 / 5.0) * 5)
    h, m = divmod(total, 60)
    return f"{h % 24:02d}:{m:02d}"


def round_minutes(hours: float, step: int = 5) -> float:
    return round(hours * 60 / step) * step / 60.0
