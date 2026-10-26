"""End-to-end smoke test of the Streamlit UI using Streamlit's headless AppTest."""

from pathlib import Path

import pytest

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr("planner.storage.DEFAULT_DB_PATH", tmp_path / "trips.db")
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception
    return at


def click(at, label):
    [b for b in at.button if b.label.startswith(label)][0].click().run()
    assert not at.exception


def test_full_user_journey(app):
    at = app
    assert len(at.tabs) == 4
    click(at, "Plan ")  # first recommendation card fills the destination
    assert at.session_state.dest_choice != "✨ Not sure yet — recommend me"
    click(at, "🗺️ Generate itinerary")
    trip = at.session_state.trip
    assert trip and len(trip["days"]) == 4

    at.text_input(key="cz_text_0_0").set_value("something cheaper or free").run()
    click(at, "Apply swap")
    click(at, "Regenerate Day 1")
    assert len(at.session_state.changes) == 2
    click(at, "Undo last change")
    assert len(at.session_state.changes) == 1

    click(at, "Save trip")
    click(at, "📂 Open in planner")
    assert at.session_state.saved_id == at.session_state.trip["id"]


def test_custom_city_in_demo_mode(app):
    at = app
    at.sidebar.selectbox(key="dest_choice").set_value("✏️ Other city…").run()
    at.sidebar.text_input(key="dest_custom").set_value("Hampi").run()
    click(at, "🗺️ Generate itinerary")
    assert at.session_state.trip["destination"]["source"] == "generic"
    assert any("template plan" in w.value for w in at.warning)
