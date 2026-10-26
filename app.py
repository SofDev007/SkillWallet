"""Personalized Travel Itinerary Planner — Streamlit entry point.

Run locally:  streamlit run app.py
"""

from __future__ import annotations

import html
import json
import os
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from planner import data
from planner.config import (
    APP_NAME, BUDGET_LEVELS, DAY_COLORS, DEFAULT_MODELS, DEFAULT_PARTY_SIZE, DIETS, INTERESTS, PACES,
    PARTY_TYPES, PROVIDER_DEMO, PROVIDERS, REGIONS, SECRET_NAMES, SLOT_ICONS, VIBES,
)
from planner.itinerary import (
    DAY_FOCUS, ai_replacement, apply_swap, build_trip, exchange_slots, find_replacement, public_view, recompute,
    regenerate_day, snapshot,
)
from planner.llm import LLMClient, LLMError
from planner.pdf_export import build_pdf
from planner.recommender import recommend, resolve_profile
from planner.storage import get_store
from planner.ui_styles import CSS
from planner.utils import convert, fmt_money

st.set_page_config(page_title=APP_NAME, page_icon="🧭", layout="wide", initial_sidebar_state="expanded")
st.markdown(CSS, unsafe_allow_html=True)

RECOMMEND_ME = "✨ Not sure yet — recommend me"
OTHER_CITY = "✏️ Other city…"
MAX_UNDO = 10


# ---------------------------------------------------------------------------
# State & helpers
# ---------------------------------------------------------------------------
def init_state() -> None:
    defaults = {
        "dest_choice": RECOMMEND_ME,
        "dest_custom": "",
        "vibe": "Any",
        "start_date": date.today() + timedelta(days=30),
        "days": 4,
        "budget": "Moderate",
        "party": "Couple",
        "travellers": DEFAULT_PARTY_SIZE["Couple"],
        "pace": "Moderate",
        "interests": ["Food", "History"],
        "diet": "No preference",
        "region": "Anywhere",
        "budget_cap": 0,
        "provider": PROVIDER_DEMO,
        "trip": None,
        "undo": [],
        "changes": [],
        "warnings": [],
        "recs": None,
        "recs_sig": None,
        "profile_cache": {},
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def secret(name: str) -> str:
    try:
        value = st.secrets.get(name, "")
    except Exception:  # no secrets.toml present
        value = ""
    return value or os.getenv(name, "")


@st.cache_resource(show_spinner=False)
def store_resource():
    return get_store(secret("SUPABASE_URL"), secret("SUPABASE_KEY"))


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def money_pair(amount: float, trip: dict) -> str:
    dest = trip["destination"]
    local = fmt_money(amount, dest["currency"])
    if dest["currency"] == "INR":
        return f"{local} · ${convert(amount, 'INR', 'USD'):,.0f}"
    inr = fmt_money(convert(amount, dest["currency"], "INR", dest["usd_per_unit"]), "INR")
    return f"{local} · {inr}"


def metric(label: str, value: str, sub: str = "") -> str:
    return (f'<div class="metric"><div class="label">{esc(label)}</div><div class="value">{esc(value)}</div>'
            f'<div class="sub">{esc(sub)}</div></div>')


def selected_destination() -> str:
    choice = st.session_state.dest_choice
    if choice == RECOMMEND_ME:
        return ""
    if choice == OTHER_CITY:
        return st.session_state.dest_custom.strip()
    return choice


def push_undo(label: str) -> None:
    st.session_state.undo.append(snapshot(st.session_state.trip))
    st.session_state.undo = st.session_state.undo[-MAX_UNDO:]
    st.session_state.changes.insert(0, label)


def plan_destination(city: str) -> None:
    """Callback used by recommendation cards to fill the destination picker."""
    if data.get_destination(city):
        st.session_state.dest_choice = data.get_destination(city)["name"]
    else:
        st.session_state.dest_choice = OTHER_CITY
        st.session_state.dest_custom = city
    st.session_state.plan_hint = city


def on_party_change() -> None:
    st.session_state.travellers = DEFAULT_PARTY_SIZE[st.session_state.party]


# ---------------------------------------------------------------------------
# Sidebar: AI configuration & preferences
# ---------------------------------------------------------------------------
def sidebar() -> tuple[LLMClient, dict]:
    sb = st.sidebar
    sb.markdown("## 🧭 Trip Studio")
    sb.markdown("#### 🔐 AI engine")
    provider = sb.radio("Provider", PROVIDERS, key="provider",
                        help="Demo mode works fully offline using a curated guide of 12 destinations.")
    api_key, model = "", ""
    if provider != PROVIDER_DEMO:
        stored = secret(SECRET_NAMES[provider])
        api_key = sb.text_input(
            f"{provider} API key", type="password", key=f"key_{provider}",
            placeholder="Loaded from secrets" if stored else "Paste your API key",
            help="Used only for this session and never stored. You can also set it in Streamlit secrets.",
        ) or stored
        with sb.expander("Advanced"):
            model = st.text_input("Model", value=DEFAULT_MODELS[provider], key=f"model_{provider}")
        if not api_key:
            sb.info("No key yet — the app keeps working in demo mode.")
    client = LLMClient(provider, api_key, model)
    if client.enabled and sb.button("Test connection", width="stretch"):
        try:
            with st.spinner("Contacting provider…"):
                client.ping()
            sb.success("Connected ✓")
        except LLMError as exc:
            sb.error(str(exc))

    sb.divider()
    sb.markdown("#### 🧳 Trip preferences")
    options = [RECOMMEND_ME, *data.list_destinations(), OTHER_CITY]
    sb.selectbox("Destination", options, key="dest_choice",
                 help="Leave on 'recommend me' and use the Destination Recommender tab to discover places.")
    if st.session_state.dest_choice == OTHER_CITY:
        sb.text_input("City name", key="dest_custom", placeholder="e.g. Kyoto, Lisbon, Udaipur")
    sb.selectbox("Travel vibe", ["Any", *VIBES], key="vibe")
    sb.date_input("Start date", key="start_date", min_value=date.today(), format="DD/MM/YYYY")
    sb.slider("Trip duration (days)", 1, 14, key="days")
    end = st.session_state.start_date + timedelta(days=st.session_state.days - 1)
    sb.caption(f"🗓️ {st.session_state.start_date:%a %d %b} → {end:%a %d %b %Y}")
    sb.select_slider("Budget level", BUDGET_LEVELS, key="budget")
    sb.selectbox("Travel party", PARTY_TYPES, key="party", on_change=on_party_change)
    sb.number_input("Travellers", min_value=1, max_value=12, step=1, key="travellers")
    sb.radio("Pace", PACES, key="pace", horizontal=True)
    sb.multiselect("Interests", INTERESTS, key="interests")
    sb.selectbox("Dietary preference", DIETS, key="diet")
    sb.selectbox("Region (for recommendations)", REGIONS, key="region")
    sb.number_input("Total budget cap in ₹ (optional)", min_value=0, step=5000, key="budget_cap",
                    help="Set 0 for no cap. The budget tracker warns you if the plan goes over.")
    sb.divider()
    sb.caption("Estimates are indicative. Verify prices, timings and visas before you travel.")

    prefs = {
        "destination": selected_destination(),
        "vibe": st.session_state.vibe,
        "start_date": st.session_state.start_date.isoformat(),
        "days": int(st.session_state.days),
        "budget": st.session_state.budget,
        "party": st.session_state.party,
        "travellers": int(st.session_state.travellers),
        "pace": st.session_state.pace,
        "interests": list(st.session_state.interests),
        "diet": st.session_state.diet,
        "region": st.session_state.region,
        "budget_cap_inr": float(st.session_state.budget_cap or 0),
    }
    return client, prefs


def hero(prefs: dict, client: LLMClient) -> None:
    chips = [
        f"📍 {prefs['destination'] or 'Destination: open'}",
        f"🌴 {prefs['vibe']} vibe",
        f"🗓️ {prefs['days']} days from {date.fromisoformat(prefs['start_date']):%d %b}",
        f"💰 {prefs['budget']}",
        f"👥 {prefs['party']} · {prefs['travellers']}",
        f"⏱️ {prefs['pace']}",
        f"🤖 {client.label}",
    ]
    st.markdown(
        f"""<div class="hero"><h1>{esc(APP_NAME)}</h1>
        <p>Optimised day-by-day plans that cluster nearby sights, track your budget and export to an offline guide.</p>
        <div class="chips">{''.join(f'<span class="chip">{esc(c)}</span>' for c in chips)}</div></div>""",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Tab 1 — Smart destination recommender
# ---------------------------------------------------------------------------
def tab_recommender(prefs: dict, client: LLMClient) -> None:
    st.subheader("Smart Destination Recommender")
    st.caption("No fixed destination? We match your vibe, travel month, budget and interests to the best-fit places.")
    sig = json.dumps({k: prefs[k] for k in ("vibe", "start_date", "budget", "party", "travellers", "interests", "region")},
                     sort_keys=True) + client.label
    run = st.button("🔮 Recommend destinations", type="primary")
    if run or (not client.enabled and st.session_state.recs_sig != sig):
        with st.spinner("Finding destinations that match your vibe…"):
            recs, warning = recommend(prefs, client)
        st.session_state.recs, st.session_state.recs_sig = recs, sig
        st.session_state.recs_warning = warning
    recs = st.session_state.recs
    if st.session_state.get("recs_warning"):
        st.warning(st.session_state.recs_warning)
    if not recs:
        st.info("Click **Recommend destinations** to get AI-powered suggestions.")
        return
    if st.session_state.recs_sig != sig:
        st.caption("⚠️ Preferences changed since these results — click the button to refresh.")

    cols = st.columns(len(recs))
    for i, (col, rec) in enumerate(zip(cols, recs)):
        with col:
            tags = "".join(f'<span class="pill">{esc(h)}</span>' for h in rec["highlights"])
            daily = f"≈ {fmt_money(rec['est_daily_cost_inr'], 'INR')} per person / day" if rec["est_daily_cost_inr"] else ""
            st.markdown(
                f"""<div class="card rec-card">
                <div class="rec-rank">#{i + 1} match</div>
                <h3>{esc(rec['city'])}</h3><div class="muted">{esc(rec['country'])}</div>
                <div class="score-bar"><span style="width:{rec['match_score']}%"></span></div>
                <div class="muted"><b>{rec['match_score']}%</b> match</div>
                <div style="margin:10px 0">{tags}</div>
                <div style="font-size:.9rem">{esc(rec['why'])}</div>
                <div style="margin-top:10px"><span class="pill sun">☀️ {esc(rec['season_note'])}</span></div>
                <div class="muted" style="margin-top:6px">{esc(daily)}</div>
                </div>""",
                unsafe_allow_html=True,
            )
            st.button(f"Plan {rec['city']} →", key=f"plan_{i}", on_click=plan_destination, args=(rec["city"],),
                      width="stretch")
            if not rec.get("curated") and not client.enabled:
                st.caption("Needs an AI key for real venues.")
    if st.session_state.get("plan_hint"):
        st.success(f"Destination set to **{st.session_state.plan_hint}**. Open the **Itinerary** tab and hit Generate.")


# ---------------------------------------------------------------------------
# Tab 2 — Itinerary generator
# ---------------------------------------------------------------------------
def generate(prefs: dict, client: LLMClient) -> None:
    city = prefs["destination"]
    cache_key = json.dumps([client.label, city.lower(), prefs["interests"], prefs["budget"], prefs["party"],
                            prefs["diet"], prefs["pace"], prefs["days"]])
    warnings = []
    with st.spinner(f"Designing your {prefs['days']}-day {city} itinerary…"):
        cache = st.session_state.profile_cache
        if client.enabled and cache_key in cache:
            profile = cache[cache_key]
        else:
            profile, warning = resolve_profile(city, prefs, client)
            if warning:
                warnings.append(warning)
            if client.enabled and profile.get("source") == "ai":
                cache[cache_key] = profile
        provider = client.label if profile.get("source") == "ai" else PROVIDER_DEMO
        trip = build_trip(profile, prefs, provider)
    st.session_state.trip = trip
    st.session_state.undo = []
    st.session_state.changes = []
    st.session_state.warnings = warnings
    st.session_state.saved_id = None


def slot_html(slot: dict, color: str, trip: dict) -> str:
    place = slot["place"]
    cls = "slot meal" if slot["kind"] == "meal" else ("slot free" if place.get("generic") and place.get("category") == "leisure" else "slot")
    icon = SLOT_ICONS.get(slot["slot"], "📍")
    tags = place.get("tags", [])[:4]
    pills = "".join(f'<span class="pill">{esc(t)}</span>' for t in tags)
    if slot["kind"] == "meal" and place.get("cuisine"):
        pills = f'<span class="pill coral">{esc(place["cuisine"])}</span>' + pills
    travel = f"🚕 {slot['travel_km']:.1f} km · ~{slot['travel_min']} min from previous" if slot["travel_km"] else "📍 Same spot as previous stop"
    cost = f"💸 {money_pair(slot['cost_local'], trip)}" if slot["cost_local"] else "💸 Free"
    return (
        f'<div class="{cls}" style="--dot:{color}"><div class="time">{icon} {esc(slot["start"])}–{esc(slot["end"])}'
        f' · {esc(slot["slot"])}</div><div class="name">{esc(place["name"])}</div>'
        f'<div class="desc">{esc(place.get("description", ""))}</div><div style="margin-top:6px">{pills}</div>'
        f'<div class="meta">{esc(travel)} &nbsp;|&nbsp; {esc(cost)}</div></div>'
    )


def render_day(day: dict, trip: dict, compact: bool = False) -> None:
    color = DAY_COLORS[(day["day"] - 1) % len(DAY_COLORS)]
    d = date.fromisoformat(day["date"])
    st.markdown(
        f'<div class="day-head"><div><span class="pill" style="background:{color};color:#fff">Day {day["day"]}</span>'
        f' <b>{d:%A, %d %b}</b> · {esc(day["theme"])}</div><div class="muted">{esc(day["area"])} · '
        f'~{day["distance_km"]:.0f} km · {esc(money_pair(day["total_local"], trip))}</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="timeline">' + "".join(slot_html(s, color, trip) for s in day["slots"]) + "</div>",
                unsafe_allow_html=True)
    if not compact:
        st.markdown("".join(f'<div class="tip">💡 {esc(t)}</div>' for t in day["tips"]), unsafe_allow_html=True)


def render_map(trip: dict) -> None:
    if trip["destination"].get("source") == "generic":
        st.info("Map hidden for template plans — add an AI key to plot real venues.")
        return
    rows = []
    for day in trip["days"]:
        color = DAY_COLORS[(day["day"] - 1) % len(DAY_COLORS)]
        for s in day["slots"]:
            p = s["place"]
            if p.get("generic"):
                continue
            rows.append({"lat": p["lat"], "lon": p["lon"], "color": color, "size": 60 if s["kind"] == "meal" else 110,
                         "name": p["name"], "day": day["day"]})
    centre = trip["destination"]["center"]
    rows.append({"lat": centre["lat"], "lon": centre["lon"], "color": "#1F2A37", "size": 160, "name": "Hotel base", "day": 0})
    st.map(pd.DataFrame(rows), latitude="lat", longitude="lon", color="color", size="size", height=380)
    legend = "".join(
        f'<span><i style="background:{DAY_COLORS[(d["day"] - 1) % len(DAY_COLORS)]}"></i>Day {d["day"]}</span>'
        for d in trip["days"]
    )
    st.markdown(f'<div class="legend">{legend}<span><i style="background:#1F2A37"></i>Hotel base (city centre)</span></div>',
                unsafe_allow_html=True)


def render_budget(trip: dict) -> None:
    dest = trip["destination"]
    ccy, rate = dest["currency"], dest["usd_per_unit"]
    rows = []
    for day in trip["days"]:
        c = day["costs"]
        rows.append({
            "Day": f"Day {day['day']}",
            "Date": date.fromisoformat(day["date"]).strftime("%d %b"),
            "Stay": fmt_money(c["stay"], ccy), "Activities": fmt_money(c["activities"], ccy),
            "Food": fmt_money(c["food"], ccy), "Transport": fmt_money(c["transport"], ccy),
            "Day total": fmt_money(day["total_local"], ccy),
            "Running total": fmt_money(day["cumulative_local"], ccy),
            "Running ₹": fmt_money(convert(day["cumulative_local"], ccy, "INR", rate), "INR"),
            "Running $": fmt_money(convert(day["cumulative_local"], ccy, "USD", rate), "USD"),
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    chart = pd.DataFrame(
        [{"Day": f"Day {d['day']:02d}", **{k.title(): round(convert(v, ccy, "INR", rate)) for k, v in d["costs"].items()}}
         for d in trip["days"]]
    ).set_index("Day")
    st.caption("Daily spend by category (₹)")
    st.bar_chart(chart, height=260, color=["#0E7C86", "#F6774F", "#FFB547", "#7B5EA7"])


def tab_itinerary(prefs: dict, client: LLMClient) -> None:
    st.subheader("Day-by-Day Optimized Itinerary")
    city = prefs["destination"]
    c1, c2 = st.columns([3, 1])
    with c1:
        if city:
            st.markdown(f"Planning **{esc(city)}** for **{prefs['days']} days** · {prefs['pace'].lower()} pace · "
                        f"{prefs['budget'].lower()} budget.")
        else:
            st.info("Choose a destination in the sidebar, or let the **Destination Recommender** tab pick one for you.")
    with c2:
        clicked = st.button("🗺️ Generate itinerary", type="primary", width="stretch", disabled=not city)
    if clicked and city:
        try:
            generate(prefs, client)
        except Exception as exc:  # keep the UI alive whatever happens
            st.error(f"Could not build the itinerary: {exc}")

    for warning in st.session_state.warnings:
        st.warning(warning)
    trip = st.session_state.trip
    if not trip:
        return

    tp = trip["preferences"]
    if any(tp.get(k) != prefs.get(k) for k in ("destination", "days", "pace", "budget", "party", "travellers",
                                                 "interests", "diet", "start_date")):
        st.caption("ℹ️ Your preferences changed since this plan was generated — click **Generate itinerary** to apply them.")

    s = trip["summary"]
    cols = st.columns(5)
    cards = [
        metric("Estimated total", fmt_money(s["total_inr"], "INR"),
               f"${s['total_usd']:,.0f}" + ("" if trip["destination"]["currency"] == "INR"
                                            else f" · {fmt_money(s['total_local'], trip['destination']['currency'])}")),
        metric("Per person", fmt_money(s["per_person_inr"], "INR"), f"{s['travellers']} traveller(s)"),
        metric("Transit saved", f"{s['transit_saved_km']:.0f} km", f"{s['transit_saved_pct']:.0f}% less vs. unclustered"),
        metric("Activities", str(s["activities"]), f"across {len(trip['days'])} days"),
        metric("Total travel", f"{s['distance_km']:.0f} km", "incl. hotel & meal legs"),
    ]
    for col, card in zip(cols, cards):
        col.markdown(card, unsafe_allow_html=True)

    if s.get("budget_cap_inr"):
        used = s["total_inr"] / s["budget_cap_inr"]
        st.progress(min(1.0, used), text=f"Budget used: {used:.0%} of {fmt_money(s['budget_cap_inr'], 'INR')}")
        if s["over_budget"]:
            st.error(f"Over budget by {fmt_money(s['total_inr'] - s['budget_cap_inr'], 'INR')}. "
                     "Try a lower budget level, fewer days, or swap paid activities in the Customize tab.")

    st.markdown(f"#### 🗺️ Route map — {esc(trip['destination']['name'])}")
    st.caption("Each colour is one day. Nearby attractions are grouped on the same day to avoid backtracking.")
    render_map(trip)

    st.markdown("#### 📅 Your plan")
    for day in trip["days"]:
        with st.expander(f"Day {day['day']} · {date.fromisoformat(day['date']):%a %d %b} · {day['theme']}",
                         expanded=day["day"] <= 2):
            render_day(day, trip)

    st.markdown("#### 💰 Running budget tracker")
    st.caption(f"Local currency: {trip['destination']['currency']}. Exchange rates are indicative.")
    render_budget(trip)

    d1, d2 = st.columns(2)
    d1.download_button("⬇️ Download itinerary JSON", json.dumps(public_view(trip), indent=2, ensure_ascii=False),
                       file_name=f"{slug(trip['title'])}.json", mime="application/json", width="stretch")
    d2.download_button("📄 Download offline PDF guide", pdf_bytes(trip), file_name=f"{slug(trip['title'])}.pdf",
                       mime="application/pdf", width="stretch")


def slug(text: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in text).strip("-").replace("--", "-") or "trip"


def pdf_bytes(trip: dict) -> bytes:
    return build_pdf(trip)


# ---------------------------------------------------------------------------
# Tab 3 — Vibe customization & dynamic swap
# ---------------------------------------------------------------------------
ACTIVITY_IDEAS = ["Swap for an outdoor market", "Find something indoors (rain plan)", "Make it more adventurous",
                  "Something cheaper or free", "Add a scenic viewpoint", "Family-friendly alternative"]
MEAL_IDEAS = ["Find a vegetarian lunch spot", "Try local street food", "Somewhere romantic",
              "Cheaper option", "Seafood place", "Vegan-friendly"]


def tab_customize(client: LLMClient) -> None:
    st.subheader("Vibe Customization & Dynamic Activity Swap")
    trip = st.session_state.trip
    if not trip:
        st.info("Generate an itinerary first — then fine-tune any slot or day here.")
        return
    st.caption("Change a single slot or regenerate one day. Every other day stays exactly as it is.")

    labels = [f"Day {d['day']} · {date.fromisoformat(d['date']):%a %d %b} · {d['theme']}" for d in trip["days"]]
    day_idx = st.selectbox("Day to customise", range(len(labels)), format_func=lambda i: labels[i], key="cz_day")
    day = trip["days"][day_idx]

    left, right = st.columns([1.1, 1])
    with left:
        st.markdown("##### 🔄 Swap a slot")
        slot_labels = [f"{s['start']} · {s['slot']} — {s['place']['name']}" for s in day["slots"]]
        slot_idx = st.selectbox("Slot", range(len(slot_labels)), format_func=lambda i: slot_labels[i],
                                key=f"cz_slot_{day_idx}")
        slot = day["slots"][slot_idx]
        ideas = MEAL_IDEAS if slot["kind"] == "meal" else ACTIVITY_IDEAS
        idea = st.pills("Quick ideas", ideas, key=f"cz_idea_{day_idx}_{slot_idx}")
        custom = st.text_input("…or describe what you want", placeholder="e.g. Swap museum for outdoor market",
                               key=f"cz_text_{day_idx}_{slot_idx}")
        instruction = (custom or idea or "").strip()
        if st.button("Apply swap", type="primary", disabled=not instruction, key="cz_apply"):
            replacement, matched, source, origin = None, False, "offline", None
            if client.enabled:
                try:
                    with st.spinner("Asking the AI for a better fit…"):
                        replacement = ai_replacement(trip, day_idx, slot_idx, instruction, client)
                    matched, source = True, "AI"
                except (LLMError, ValueError) as exc:
                    st.warning(f"AI swap unavailable ({exc}); using the offline matcher.")
            if replacement is None:
                replacement, matched, origin = find_replacement(trip, day_idx, slot_idx, instruction)
            if replacement is None:
                st.error("No unused alternatives left near this area. Try regenerating the day instead.")
            else:
                old = slot["place"]["name"]
                push_undo(f"Day {day['day']}: {old} → {replacement['name']} ({instruction})")
                note = "" if matched else " (closest alternative — no exact match for that request)"
                if origin:
                    exchange_slots(trip, (day_idx, slot_idx), origin)
                    note += f". Every suitable stop was already planned, so **{old}** moved to Day {origin[0] + 1}"
                else:
                    apply_swap(trip, day_idx, slot_idx, replacement)
                st.session_state.flash = f"Swapped **{old}** for **{replacement['name']}** via {source} matcher{note}."
                st.rerun()

    with right:
        st.markdown("##### ♻️ Regenerate this day")
        focus = st.selectbox("Give the day a vibe", list(DAY_FOCUS), key=f"cz_focus_{day_idx}")
        if st.button(f"Regenerate Day {day['day']}", key="cz_regen", width="stretch"):
            push_undo(f"Day {day['day']} regenerated ({focus})")
            regenerate_day(trip, day_idx, focus, seed=len(st.session_state.changes))
            st.session_state.flash = f"Day {day['day']} rebuilt with a **{focus.lower()}** vibe. Other days untouched."
            st.rerun()
        st.markdown("##### ↩️ History")
        if st.button("Undo last change", disabled=not st.session_state.undo, width="stretch"):
            st.session_state.trip = st.session_state.undo.pop()
            undone = st.session_state.changes.pop(0) if st.session_state.changes else "change"
            st.session_state.flash = f"Undid: {undone}"
            st.rerun()
        if st.session_state.changes:
            st.markdown("\n".join(f"- {esc(c)}" for c in st.session_state.changes[:6]))
        else:
            st.caption("No edits yet.")

    if st.session_state.get("flash"):
        st.success(st.session_state.pop("flash"))
    st.divider()
    render_day(trip["days"][day_idx], trip)


# ---------------------------------------------------------------------------
# Tab 4 — Trip management & offline PDF export
# ---------------------------------------------------------------------------
def tab_manage() -> None:
    st.subheader("Trip Management & Offline PDF Export")
    store, store_warning = store_resource()
    if store_warning:
        st.warning(store_warning)
    stats_box = st.container()  # filled after any save/delete below so the numbers are current

    trip = st.session_state.trip
    st.markdown("##### 💾 Save the current trip")
    if trip:
        c1, c2, c3 = st.columns([2.2, 1, 1.2])
        title = c1.text_input("Trip name", value=trip["title"], key=f"save_title_{trip['id']}")
        c2.write("")
        c2.write("")
        if c2.button("Save trip", type="primary", width="stretch"):
            trip["title"] = title.strip() or trip["title"]
            try:
                store.save(trip)
                st.session_state.saved_id = trip["id"]
                st.toast(f"Saved “{trip['title']}”", icon="💾")
            except Exception as exc:
                st.error(f"Could not save: {exc}")
        c3.write("")
        c3.write("")
        c3.download_button("📄 Offline PDF guide", pdf_bytes(trip), file_name=f"{slug(trip['title'])}.pdf",
                           mime="application/pdf", type="primary", width="stretch", key="pdf_current")
        if st.session_state.get("saved_id") == trip["id"]:
            st.caption("✅ Saved. Saving again updates the same record.")
    else:
        st.caption("Generate an itinerary to save or export it.")

    st.markdown("##### 🗂️ Trip history")
    try:
        trips = store.list()
        stats = store.stats()
    except Exception as exc:
        st.error(f"Storage error: {exc}")
        return
    with stats_box:
        cols = st.columns(4)
        cols[0].markdown(metric("Saved trips", str(stats["trips"]), f"{store.backend} · {store.location}"),
                         unsafe_allow_html=True)
        cols[1].markdown(metric("Days planned", str(stats["days"])), unsafe_allow_html=True)
        cols[2].markdown(metric("Destinations", str(stats["destinations"])), unsafe_allow_html=True)
        cols[3].markdown(metric("Activities logged",
                                str(stats["activities"] if stats["activities"] is not None else "—")),
                         unsafe_allow_html=True)
    if not trips:
        st.info("No saved trips yet. Your saved plans will appear here.")
        return
    table = pd.DataFrame([{
        "Trip": t["title"], "Destination": t["destination"], "Starts": t["start_date"], "Days": t["days"],
        "Party": f"{t['party']} ({t['travellers']})", "Budget": t["budget_level"],
        "Est. total": fmt_money(t["total_inr"] or 0, "INR"), "Saved": (t["updated_at"] or "").replace("T", " ")[:16],
    } for t in trips])
    st.dataframe(table, hide_index=True, width="stretch")

    by_id = {t["id"]: t for t in trips}
    pick = st.selectbox("Select a saved trip", list(by_id), format_func=lambda i: f"{by_id[i]['title']} — {by_id[i]['destination']}",
                        key="history_pick")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📂 Open in planner", width="stretch"):
        loaded = store.load(pick)
        if loaded:
            st.session_state.trip = recompute(loaded)
            st.session_state.undo, st.session_state.changes, st.session_state.warnings = [], [], []
            st.session_state.saved_id = pick
            st.success("Loaded — see the Itinerary and Customize tabs.")
    selected = store.load(pick)
    if selected:
        c2.download_button("📄 PDF", pdf_bytes(selected), file_name=f"{slug(selected['title'])}.pdf",
                           mime="application/pdf", width="stretch", key=f"pdf_{pick}")
        c3.download_button("⬇️ JSON", json.dumps(public_view(selected), indent=2, ensure_ascii=False),
                           file_name=f"{slug(selected['title'])}.json", mime="application/json",
                           width="stretch", key=f"json_{pick}")
    confirm = c4.checkbox("Confirm delete", key=f"confirm_{pick}")
    if c4.button("🗑️ Delete", disabled=not confirm, width="stretch"):
        store.delete(pick)
        st.toast("Trip deleted", icon="🗑️")
        st.rerun()

    if trip:
        with st.expander("🚨 Emergency contacts for your current destination"):
            for service, number in trip["destination"].get("emergency", {}).items():
                st.markdown(f"- **{esc(service)}:** {esc(number)}")
            st.caption("The PDF guide also includes a fill-in contact sheet and a pre-departure checklist.")


# ---------------------------------------------------------------------------
def main() -> None:
    init_state()
    client, prefs = sidebar()
    hero(prefs, client)
    t1, t2, t3, t4 = st.tabs(["🔮 Destination Recommender", "🗺️ Itinerary", "🎛️ Customize & Swap", "🗂️ My Trips & PDF"])
    with t1:
        tab_recommender(prefs, client)
    with t2:
        tab_itinerary(prefs, client)
    with t3:
        tab_customize(client)
    with t4:
        tab_manage()


main()
