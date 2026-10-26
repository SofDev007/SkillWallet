"""Static configuration: option lists, slot definitions, currency tables and tuning knobs."""

APP_NAME = "Personalized Travel Itinerary Planner"
SCHEMA_VERSION = "1.0"

# ---------------------------------------------------------------------------
# Preference options
# ---------------------------------------------------------------------------
VIBES = ["Beach", "Mountains", "Cultural", "Urban"]
BUDGET_LEVELS = ["Budget", "Moderate", "Luxury"]
PARTY_TYPES = ["Solo", "Couple", "Family", "Friends"]
DEFAULT_PARTY_SIZE = {"Solo": 1, "Couple": 2, "Family": 4, "Friends": 4}
PACES = ["Relaxed", "Moderate", "Fast-Paced"]
INTERESTS = ["Food", "Adventure", "History", "Nightlife", "Culture", "Nature", "Shopping", "Wellness"]
DIETS = ["No preference", "Vegetarian", "Vegan"]
REGIONS = ["Anywhere", "India only", "International only"]

# Which place categories satisfy each interest / vibe.
INTEREST_CATEGORIES = {
    "Food": {"food"},
    "Adventure": {"adventure"},
    "History": {"history"},
    "Nightlife": {"nightlife"},
    "Culture": {"culture"},
    "Nature": {"nature", "beach"},
    "Shopping": {"shopping"},
    "Wellness": {"wellness"},
}
INTEREST_TAGS = {
    "Food": {"market", "street-food", "food"},
    "Adventure": {"trek", "watersports", "adventure"},
    "History": {"heritage", "unesco", "museum"},
    "Nightlife": {"nightlife", "bar", "evening"},
    "Culture": {"art", "temple", "museum", "performance"},
    "Nature": {"views", "waterfall", "park", "garden"},
    "Shopping": {"market", "souvenirs"},
    "Wellness": {"spa", "yoga", "hot-springs"},
}
VIBE_CATEGORIES = {
    "Beach": {"beach"},
    "Mountains": {"nature", "adventure"},
    "Cultural": {"history", "culture"},
    "Urban": {"shopping", "landmark", "food", "nightlife"},
}

# ---------------------------------------------------------------------------
# Day structure
# ---------------------------------------------------------------------------
SLOT_MORNING = "Morning Sightseeing"
SLOT_LUNCH = "Lunch Recommendation"
SLOT_AFTERNOON = "Afternoon Leisure"
SLOT_DINNER = "Evening Dining & Entertainment"
SLOT_EVENING = "Evening Entertainment"
SLOT_ORDER = [SLOT_MORNING, SLOT_LUNCH, SLOT_AFTERNOON, SLOT_DINNER, SLOT_EVENING]
SLOT_ICONS = {
    SLOT_MORNING: "🌅",
    SLOT_LUNCH: "🍽️",
    SLOT_AFTERNOON: "🏖️",
    SLOT_DINNER: "🌙",
    SLOT_EVENING: "🎭",
}

# (morning activities, afternoon activities) per pace.
PACE_SLOTS = {"Relaxed": (1, 1), "Moderate": (1, 2), "Fast-Paced": (2, 2)}
# Hour the day starts for each pace.
PACE_START_HOUR = {"Relaxed": 10.0, "Moderate": 9.0, "Fast-Paced": 8.0}

LUNCH_EARLIEST = 12.5
LUNCH_DURATION = 1.25
DINNER_EARLIEST = 19.0
DINNER_DURATION = 1.75
EVENING_DURATION = 1.5

FULL_DAY_HOURS = 5.0          # an activity this long becomes a full-day excursion
MEAL_SEARCH_RADIUS_KM = 20.0   # beyond this we suggest a generic local meal instead
EVENING_SEARCH_RADIUS_KM = 15.0

ROAD_FACTOR = 1.3             # straight-line km -> approximate road km
CITY_SPEED_KMH = 25.0         # average door-to-door urban speed for travel-time estimates

# ---------------------------------------------------------------------------
# Money
# ---------------------------------------------------------------------------
# Indicative exchange rates (USD value of one unit). Edit here to refresh.
USD_PER_UNIT = {
    "USD": 1.0,
    "INR": 1 / 88.0,
    "EUR": 1.08,
    "GBP": 1.27,
    "JPY": 1 / 150.0,
    "CHF": 1.12,
    "AED": 0.2723,
    "THB": 1 / 35.0,
    "IDR": 1 / 16000.0,
    "SGD": 0.74,
    "LKR": 1 / 300.0,
    "NPR": 1 / 140.0,
    "MYR": 0.21,
    "VND": 1 / 25000.0,
    "AUD": 0.65,
    "CAD": 0.73,
    "TRY": 1 / 34.0,
}
CURRENCY_SYMBOLS = {
    "USD": "$", "INR": "₹", "EUR": "€", "GBP": "£", "JPY": "¥", "CHF": "CHF ",
    "AED": "AED ", "THB": "฿", "IDR": "Rp ", "SGD": "S$", "LKR": "Rs ", "NPR": "Rs ",
    "MYR": "RM ", "VND": "₫", "AUD": "A$", "CAD": "C$", "TRY": "₺",
}

# Restaurant price tier preferred for each budget level.
BUDGET_TARGET_TIER = {"Budget": 1, "Moderate": 2, "Luxury": 3}

# Colours used to tell days apart on the map and in charts.
DAY_COLORS = [
    "#0E9AA7", "#F6774F", "#7B5EA7", "#3DA35D", "#E8A33D", "#D64570", "#2F6690",
    "#8C6D31", "#00A6A6", "#C44536", "#5B8E7D", "#9A4C95", "#4F6D7A", "#B5838D",
]

# ---------------------------------------------------------------------------
# AI providers
# ---------------------------------------------------------------------------
PROVIDER_DEMO = "Demo mode (offline)"
PROVIDER_GEMINI = "Google Gemini"
PROVIDER_GROQ = "Groq"
PROVIDERS = [PROVIDER_DEMO, PROVIDER_GEMINI, PROVIDER_GROQ]
DEFAULT_MODELS = {PROVIDER_GEMINI: "gemini-2.5-flash", PROVIDER_GROQ: "llama-3.3-70b-versatile"}
SECRET_NAMES = {PROVIDER_GEMINI: "GEMINI_API_KEY", PROVIDER_GROQ: "GROQ_API_KEY"}
