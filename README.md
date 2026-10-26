# 🧭 Personalized Travel Itinerary Planner

An AI-powered trip-planning web app that builds **optimised day-by-day itineraries**, groups nearby attractions so you don't zig-zag across the city, recommends destinations when you only know the *vibe* you want, tracks a running budget in local currency, INR and USD, and exports a **printable offline PDF travel guide**.

Built with **Python + Streamlit**. Works **fully offline in demo mode** (curated guide of 12 destinations) and switches to **Google Gemini** or **Groq** for live AI planning of any city on Earth.

---

## ✨ Features

| Area | What it does |
|---|---|
| **Preferences (sidebar)** | AI provider + API key (or demo mode), destination *or* open-ended vibe (Beach / Mountains / Cultural / Urban), start date + duration, budget level (Budget / Moderate / Luxury), travel party (Solo / Couple / Family / Friends) and head-count, pace (Relaxed / Moderate / Fast-Paced), interests (Food, Adventure, History, Nightlife, Culture, Nature, Shopping, Wellness), diet, region and an optional ₹ budget cap. |
| **Tab 1 – Smart Destination Recommender** | Top-3 destinations scored on vibe, weather season for your travel month, budget fit, interests, party type and region. Each card shows highlight tags, a "why it fits" explanation, a season note and an estimated ₹/person/day. One click sends the pick to the planner. |
| **Tab 2 – Day-by-Day Optimised Itinerary** | Time-slotted days (🌅 Morning Sightseeing → 🍽️ Lunch → 🏖️ Afternoon Leisure → 🌙 Evening Dining & Entertainment, plus optional 🎭 evening shows). **Geographic clustering** keeps each day in one area; a colour-coded route map, travel time/distance between stops, itemised costs, and a **running cumulative budget tracker** in local currency, ₹ and $ with a daily spend chart. |
| **Tab 3 – Vibe Customisation & Dynamic Swap** | Swap any single slot with quick ideas ("Swap for an outdoor market", "Find a vegetarian lunch spot", "Find something indoors (rain plan)") or free text; regenerate **one** day with a new vibe (Adventure, Culture & history, Food trail…) without touching the rest; full **undo** history. |
| **Tab 4 – Trip Management & Offline PDF** | Save/update trips to a database, browse trip history, reopen, delete, and download any trip as **PDF** or **JSON**. The PDF includes the budget overview, every day's schedule, local emergency numbers, a fill-in emergency-contact sheet and a pre-departure checklist. |

### How the route optimisation works
1. Attractions are ranked against your interests, vibe, party type, budget, season and pace.
2. Long excursions (≥ 5 h, e.g. a volcano trek or palace day-trip) get a day of their own.
3. The rest are split into one cluster per day using a **capacity-balanced k-means** (several seeds), then refined by **local search** that swaps stops between days whenever the total route gets shorter.
4. Each day's visiting order is the **shortest hotel → stops → hotel loop** (exact search for ≤ 6 stops), with sunset spots pinned to the end of the day.
5. Lunch and dinner are picked near where you'll actually be, filtered by budget tier and diet.

The app reports the saving versus an un-clustered plan — on the bundled destinations this averages **~25 % less transit**.

---

## 🗂️ Project structure

```
travel-itinerary-planner/
├── app.py                    # Streamlit UI (sidebar + 4 tabs)
├── planner/
│   ├── config.py             # options, slot timings, currencies, provider defaults
│   ├── data.py               # curated offline destination guide (12 cities) + generic fallback
│   ├── schemas.py            # JSON data contracts + validation/coercion of AI output
│   ├── llm.py                # Gemini & Groq REST clients (strict JSON mode, friendly errors)
│   ├── prompts.py            # prompt templates embedding the JSON contracts
│   ├── recommender.py        # destination scoring, AI recommendations, profile resolution
│   ├── itinerary.py          # clustering, routing, scheduling, budgeting, swaps, day regeneration
│   ├── storage.py            # SQLite persistence (default) + optional Supabase backend
│   ├── pdf_export.py         # ReportLab offline travel guide
│   ├── ui_styles.py          # wanderlust-inspired CSS theme
│   └── utils.py              # haversine distance, money & time formatting
├── db/
│   ├── schema.sql            # SQLite schema (auto-created on first run)
│   └── supabase_schema.sql   # optional PostgreSQL schema for Supabase
├── tests/                    # 180 pytest tests incl. a headless end-to-end UI test
├── .streamlit/
│   ├── config.toml           # theme
│   └── secrets.toml.example  # template for API keys
├── requirements.txt
└── requirements-dev.txt
```

### Architecture

```
 Sidebar preferences ──► recommender.py ──► (Gemini / Groq JSON)  ─┐
                                   │                                 │ validate (schemas.py)
                                   └──► data.py (offline guide) ◄────┘ fallback on any error
                                              │
                                   destination profile (one JSON contract)
                                              ▼
                     itinerary.py: rank → cluster → route → meals → schedule → budget
                                              ▼
                  Streamlit tabs ◄──► storage.py (SQLite | Supabase) ──► pdf_export.py
```

Every AI response is validated and coerced (types, coordinates within range of the city, categories, price tiers). If the provider is unreachable, the key is wrong, or the JSON is unusable, the app shows a warning and **falls back to offline data** instead of crashing.

---

## 🚀 Run locally

Requires **Python 3.9+** (3.11 or 3.12 recommended).

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501. Everything works immediately in **Demo mode (offline)**.

### Optional: enable live AI planning
Pick **Google Gemini** or **Groq** in the sidebar and paste a key, or store it in `.streamlit/secrets.toml` (copy from `secrets.toml.example`):

```toml
GEMINI_API_KEY = "..."   # https://aistudio.google.com/app/apikey
GROQ_API_KEY   = "..."   # https://console.groq.com/keys
```

Default models are `gemini-2.5-flash` and `llama-3.3-70b-versatile`; change them under **Advanced** in the sidebar if your account uses different ones. Use **Test connection** to verify a key.

With AI enabled you can plan **any** city (type it under "Other city…"), get open-world destination recommendations, and AI-powered slot swaps.

---

## ☁️ Deploy free on Streamlit Community Cloud

1. Push this folder to a **public GitHub repository** (`app.py` must be at the repo root):
   ```bash
   git init
   git add .
   git commit -m "Personalized Travel Itinerary Planner"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo>.git
   git push -u origin main
   ```
2. Go to **https://share.streamlit.io** → **Create app** → choose the repo, branch `main`, main file `app.py`.
3. (Optional) In **Advanced settings** pick Python 3.11/3.12 and paste your keys into **Secrets** using the format from `.streamlit/secrets.toml.example`.
4. Click **Deploy**. You'll get a public `https://<app-name>.streamlit.app` URL.

No database server is needed: trips are stored in a local SQLite file. Note that Streamlit Cloud's disk is **ephemeral** — saved trips survive while the app is running but reset when it restarts or redeploys. For permanent storage, create a free Supabase project, run `db/supabase_schema.sql` in its SQL editor and add `SUPABASE_URL` and `SUPABASE_KEY` to the app's secrets; the app switches backends automatically (and falls back to SQLite if Supabase is unreachable).

---

## 🧪 Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

Covers itinerary generation for every destination × pace × trip length, clustering balance and route savings, budget maths, diet handling, swap/regenerate/undo behaviour, AI-output validation and fallback paths (with mocked Gemini/Groq HTTP), SQLite round-trips, PDF generation with tricky Unicode/markup, and a headless end-to-end run of the Streamlit UI (`streamlit.testing.v1.AppTest`).

---

## 📐 Data contracts

All modules exchange plain JSON-serialisable dictionaries.

**Destination profile** (returned by the offline guide *and* requested from the AI):
```json
{
  "name": "Goa", "country": "India", "currency": "INR",
  "center": {"lat": 15.53, "lon": 73.80},
  "best_months": [11, 12, 1, 2, 3], "avoid_months": {"7": "Monsoon"},
  "hotel": {"Budget": 2000, "Moderate": 5000, "Luxury": 15000},
  "transport_per_km": 25,
  "emergency": {"Police": "100 / 112", "Ambulance": "108"},
  "places": [{"name": "...", "category": "history", "lat": 0, "lon": 0, "cost": 0,
              "duration": 1.5, "tags": ["iconic"], "indoor": true, "description": "..."}],
  "restaurants": [{"name": "...", "lat": 0, "lon": 0, "cost": 800, "tier": 2,
                   "cuisine": "Goan", "tags": ["vegetarian"], "description": "..."}]
}
```

**Trip** (what is saved, exported to JSON and rendered to PDF):
```json
{
  "schema_version": "1.0", "id": "a1b2c3d4e5f6", "title": "Goa · 4 days",
  "provider": "Demo mode (offline)",
  "destination": {"name": "Goa", "currency": "INR", "usd_per_unit": 0.0114, "center": {}, "emergency": {}},
  "preferences": {"vibe": "Beach", "days": 4, "start_date": "2026-11-25", "budget": "Moderate", "...": "..."},
  "days": [{
    "day": 1, "date": "2026-11-25", "theme": "Heritage & History", "area": "Around Old Goa",
    "slots": [{"slot": "Morning Sightseeing", "kind": "activity", "start": "09:15", "end": "10:45",
               "place": {"name": "..."}, "travel_km": 6.6, "travel_min": 15, "cost_local": 0}],
    "distance_km": 42.0, "costs": {"stay": 5000, "activities": 1000, "food": 3400, "transport": 1048},
    "total_local": 10448, "cumulative_local": 10448, "tips": ["..."]
  }],
  "summary": {"total_local": 41270, "total_inr": 41270, "total_usd": 469, "per_person_inr": 20635,
              "transit_saved_km": 83, "transit_saved_pct": 38, "by_category": {}}
}
```

---

## ⚠️ Known limitations

- Prices, opening hours and exchange rates are **indicative estimates** (rates live in `planner/config.py`). Always confirm locally.
- The offline guide covers 12 destinations (Goa, Manali, Jaipur, Mumbai, Kochi, Bali, Paris, Tokyo, Interlaken, Dubai, Bangkok, Rome). Other cities in demo mode get a clearly-labelled template plan; add an AI key for real venues.
- Distances are straight-line × 1.3 road factor, and travel times assume ~25 km/h door-to-door, not live traffic or transit timetables.
- Day-of-week specifics (e.g. weekend-only markets) aren't enforced — check the description of market stops.
- The map needs internet access to load base tiles.
- The demo database is shared by everyone using a deployed instance; don't store anything private in trip names.
