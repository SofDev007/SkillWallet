"""Offline PDF travel guide built with ReportLab."""

from __future__ import annotations

import io
from datetime import date
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    CondPageBreak, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from .config import APP_NAME
from .utils import convert, fmt_money

TEAL = colors.HexColor("#0E7C86")
CORAL = colors.HexColor("#F6774F")
SAND = colors.HexColor("#FFF6EC")
INK = colors.HexColor("#1F2A37")
MUTED = colors.HexColor("#6B7280")
LINE = colors.HexColor("#E5E7EB")


def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=24,
                                textColor=TEAL, leading=28, spaceAfter=4),
        "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontSize=11, textColor=MUTED, leading=14),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=14,
                             textColor=INK, spaceBefore=10, spaceAfter=4),
        "h3": ParagraphStyle("h3", parent=base["Heading3"], fontName="Helvetica-Bold", fontSize=11.5,
                             textColor=TEAL, spaceBefore=6, spaceAfter=2),
        "body": ParagraphStyle("body", parent=base["Normal"], fontSize=9.5, textColor=INK, leading=12.5),
        "small": ParagraphStyle("small", parent=base["Normal"], fontSize=8, textColor=MUTED, leading=10),
        "cell": ParagraphStyle("cell", parent=base["Normal"], fontSize=8.8, textColor=INK, leading=11),
        "cellb": ParagraphStyle("cellb", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8.8,
                                textColor=INK, leading=11),
        "center": ParagraphStyle("center", parent=base["Normal"], fontSize=8, textColor=MUTED, alignment=TA_CENTER),
    }


_ASCII_MAP = str.maketrans({"\u2014": "-", "\u2013": "-", "\u2018": "'", "\u2019": "'", "\u201c": '"',
                            "\u201d": '"', "\u2026": "...", "\u20b9": "INR ", "\u2192": "->", "\u00a0": " "})


def _latin1(text: str) -> str:
    """Built-in PDF fonts only cover Latin-1, so normalise punctuation and replace the rest."""
    return str(text).translate(_ASCII_MAP).encode("latin-1", "replace").decode("latin-1")


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    """Paragraph with XML-escaped, Latin-1-safe text."""
    return Paragraph(escape(_latin1(text)), style)


def _table(rows: list[list], widths: list[float], header: bool = True, zebra: bool = True) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.8),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), TEAL), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                  ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    if zebra:
        for r in range(1 if header else 0, len(rows)):
            if r % 2 == 0:
                style.append(("BACKGROUND", (0, r), (-1, r), SAND))
    table.setStyle(TableStyle(style))
    return table


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFillColor(CORAL)
    canvas.rect(0, A4[1] - 6 * mm, A4[0], 6 * mm, stroke=0, fill=1)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(15 * mm, 10 * mm, f"{APP_NAME} - all prices are indicative estimates; verify before travel.")
    canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf(trip: dict) -> bytes:
    """Render ``trip`` to PDF bytes."""
    st = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=16 * mm, bottomMargin=18 * mm,
                            title=f"{trip['destination']['name']} itinerary", author=APP_NAME)
    dest, prefs, summary = trip["destination"], trip["preferences"], trip["summary"]
    ccy, rate = dest["currency"], dest["usd_per_unit"]

    def money(x: float) -> str:
        local = fmt_money(x, ccy, ascii_only=True)
        if ccy == "INR":
            return local
        return f"{local} (INR {round(convert(x, ccy, 'INR', rate)):,})"

    story = []
    start = date.fromisoformat(trip["days"][0]["date"]) if trip["days"] else date.today()
    end = date.fromisoformat(trip["days"][-1]["date"]) if trip["days"] else start
    place_line = ", ".join(x for x in (dest["name"], dest.get("country")) if x)
    story += [
        _p(trip.get("title") or dest["name"], st["title"]),
        _p(f"{place_line}  |  {start:%a %d %b %Y} - {end:%a %d %b %Y}", st["subtitle"]),
        Spacer(1, 8),
    ]
    facts = [
        ["Travellers", f"{prefs.get('party')} ({summary.get('travellers', 1)})", "Budget level", prefs.get("budget", "")],
        ["Pace", prefs.get("pace", ""), "Interests", ", ".join(prefs.get("interests") or []) or "-"],
        ["Diet", prefs.get("diet", "-"), "Planned with", trip.get("provider", "")],
    ]
    story.append(_table([[_p(c, st["cellb"] if i % 2 == 0 else st["cell"]) for i, c in enumerate(r)] for r in facts],
                        [28 * mm, 62 * mm, 28 * mm, 62 * mm], header=False))
    story.append(Spacer(1, 8))

    story.append(_p("Budget overview", st["h2"]))
    cat = summary["by_category"]
    budget_rows = [["Category", "Estimated cost"]] + [
        [label, money(cat[key])] for key, label in
        (("stay", f"Accommodation ({summary.get('nights', 0)} nights)"), ("activities", "Sightseeing & activities"),
         ("food", "Food & dining"), ("transport", "Local transport"))
    ] + [["Total", money(summary["total_local"])], ["Total (USD)", f"USD {round(summary['total_usd']):,}"]]
    story.append(_table([[_p(c, st["cellb"] if r >= len(budget_rows) - 2 else st["cell"]) for c in row]
                         for r, row in enumerate(budget_rows)], [90 * mm, 90 * mm]))
    if summary.get("transit_saved_km"):
        story.append(Spacer(1, 4))
        story.append(_p(
            f"Route optimisation: attractions are grouped by neighbourhood, cutting sightseeing transit by about "
            f"{summary['transit_saved_km']:.0f} km ({summary['transit_saved_pct']:.0f}%) versus an unclustered plan.",
            st["small"]))

    story.append(_p("Day-by-day itinerary", st["h2"]))
    for day in trip["days"]:
        d = date.fromisoformat(day["date"])
        block = [_p(f"Day {day['day']} - {d:%A, %d %b}  |  {day['theme']}", st["h3"]),
                 _p(f"{day['area']}  |  ~{day['distance_km']:.0f} km of travel  |  Day total {money(day['total_local'])}",
                    st["small"]), Spacer(1, 3)]
        rows = [["Time", "Slot", "Plan", "Est. cost"]]
        for s in day["slots"]:
            place = s["place"]
            detail = f"<b>{escape(_latin1(place['name']))}</b>"
            if place.get("description"):
                detail += f"<br/><font color='#6B7280'>{escape(_latin1(place['description']))}</font>"
            if s.get("travel_km"):
                detail += f"<br/><font color='#0E7C86'>~{s['travel_km']:.1f} km / {s['travel_min']} min from previous stop</font>"
            rows.append([_p(f"{s['start']}-{s['end']}", st["cell"]), _p(s["slot"], st["cell"]),
                         Paragraph(detail, st["cell"]), _p(fmt_money(s["cost_local"], ccy, ascii_only=True), st["cell"])])
        block.append(_table(rows, [22 * mm, 36 * mm, 92 * mm, 30 * mm]))
        if day.get("tips"):
            block.append(Spacer(1, 3))
            block += [_p(f"- {tip}", st["small"]) for tip in day["tips"]]
        block.append(Spacer(1, 6))
        story.append(CondPageBreak(60 * mm))
        story.append(KeepTogether(block[:4]))
        story += block[4:]

    story.append(PageBreak())
    story.append(_p("Emergency contacts & safety checklist", st["h2"]))
    emergency = dest.get("emergency") or {"General emergency": "112"}
    story.append(_table([["Service", "Number"]] + [[_p(k, st["cell"]), _p(v, st["cellb"])] for k, v in emergency.items()],
                        [90 * mm, 90 * mm]))
    story.append(Spacer(1, 8))
    personal = [["Contact", "Details (fill in before you go)"],
                ["Hotel name & address", ""], ["Emergency contact at home", ""], ["Travel insurance policy no.", ""],
                ["Insurer 24x7 helpline", ""], ["Nearest embassy / consulate", ""], ["Local guide / driver", ""]]
    personal_rows = [[personal[0][0], personal[0][1]]] + [[_p(r[0], st["cell"]), ""] for r in personal[1:]]
    story.append(_table(personal_rows, [70 * mm, 110 * mm]))
    story.append(Spacer(1, 8))
    story.append(_p("Pre-departure checklist", st["h3"]))
    checklist = [
        "Passport / government ID (plus photocopies and a digital copy)",
        "Visa or entry permits checked for every traveller",
        "Travel insurance documents saved offline",
        "Hotel and transport bookings confirmed",
        "Offline maps of the destination downloaded",
        "Local SIM / roaming pack and power adapter",
        "Prescription medicines and a basic first-aid kit",
        "Cards notified for international use; some cash in local currency",
        "Share this itinerary with a family member or friend",
        "Weather-appropriate clothing (check forecast 48 h before)",
    ]
    story.append(_table([[_p("[  ]", st["cellb"]), _p(item, st["cell"])] for item in checklist],
                        [12 * mm, 168 * mm], header=False, zebra=False))
    story.append(Spacer(1, 10))
    story.append(_p("Generated offline. Opening hours, prices and exchange rates change - confirm locally.", st["center"]))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
