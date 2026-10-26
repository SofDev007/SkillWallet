import pytest

from planner import recommender
from planner.config import PROVIDER_GEMINI
from planner.llm import LLMClient, LLMError, extract_json
from planner.schemas import validate_profile, validate_recommendations


def test_extract_json_handles_fences_and_prose():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Sure! Here it is: {"a": [1, 2]} hope that helps') == {"a": [1, 2]}
    with pytest.raises(LLMError):
        extract_json("no json here")


def _profile(n_places=6):
    return {
        "name": "Lisbon", "country": "Portugal", "currency": "EUR", "center": {"lat": 38.72, "lon": -9.14},
        "places": [
            {"name": f"Place {i}", "category": "culture", "lat": 38.72 + i * 0.003, "lon": -9.14, "cost": "€10",
             "duration": "2", "tags": "views, iconic", "indoor": False, "description": "x"}
            for i in range(n_places)
        ] + [{"name": "Far away", "category": "culture", "lat": 10.0, "lon": 10.0}],
        "restaurants": [{"name": "Taberna", "lat": 38.71, "lon": -9.13, "cost": 20, "tier": 9, "tags": ["local"]}],
        "hotel": {"Budget": 70},
        "avoid_months": {"8": "Crowds", "13": "bogus"},
    }


def test_validate_profile_coerces_and_filters():
    profile = validate_profile(_profile(), "Lisbon")
    assert len(profile["places"]) == 6  # far-away place dropped
    assert profile["places"][0]["cost"] == 10.0 and profile["places"][0]["tags"] == ["views", "iconic"]
    assert profile["restaurants"][0]["tier"] == 3
    assert profile["avoid_months"] == {8: "Crowds"}
    assert set(profile["hotel"]) == {"Budget", "Moderate", "Luxury"}


def test_validate_profile_rejects_thin_output():
    with pytest.raises(ValueError):
        validate_profile(_profile(n_places=2), "Lisbon")


def test_validate_recommendations():
    recs = validate_recommendations({"recommendations": [{"city": "Hampi", "match_score": 140}, {"bad": 1}]})
    assert recs[0]["city"] == "Hampi" and recs[0]["match_score"] == 100


class FakeClient(LLMClient):
    def __init__(self, reply=None, error=None):
        super().__init__(PROVIDER_GEMINI, "test-key")
        self.reply, self.error = reply, error

    def generate_json(self, system, user, temperature=0.4):
        if self.error:
            raise self.error
        return self.reply


def test_ai_profile_is_used_when_valid():
    profile, warning = recommender.resolve_profile("Lisbon", {"days": 3}, FakeClient(reply=_profile()))
    assert profile["source"] == "ai" and warning is None


def test_ai_failure_falls_back_to_curated_data():
    profile, warning = recommender.resolve_profile("Goa", {"days": 3}, FakeClient(error=LLMError("HTTP 401")))
    assert profile["source"] == "curated" and "401" in warning


def test_ai_recommendation_failure_falls_back():
    prefs = {"vibe": "Beach", "start_date": "2026-12-01", "budget": "Moderate", "interests": [], "region": "Anywhere"}
    recs, warning = recommender.recommend(prefs, FakeClient(error=LLMError("timeout")))
    assert len(recs) == 3 and "timeout" in warning


class FakeResponse:
    def __init__(self, status, payload):
        self.status_code, self._payload = status, payload

    def json(self):
        return self._payload


def test_gemini_request_and_parsing(monkeypatch):
    seen = {}

    def fake_post(url, headers, json, timeout):
        seen.update(url=url, headers=headers, body=json)
        return FakeResponse(200, {"candidates": [{"content": {"parts": [{"text": '{"status": "ok"}'}]}}]})

    monkeypatch.setattr("planner.llm.requests.post", fake_post)
    client = LLMClient(PROVIDER_GEMINI, "secret-key", "gemini-test")
    assert client.ping() == "ok"
    assert "gemini-test:generateContent" in seen["url"]
    assert seen["headers"]["x-goog-api-key"] == "secret-key"
    assert seen["body"]["generationConfig"]["responseMimeType"] == "application/json"


def test_groq_request_and_parsing(monkeypatch):
    from planner.config import PROVIDER_GROQ

    def fake_post(url, headers, json, timeout):
        assert headers["Authorization"] == "Bearer k" and json["response_format"] == {"type": "json_object"}
        return FakeResponse(200, {"choices": [{"message": {"content": '{"status": "ok"}'}}]})

    monkeypatch.setattr("planner.llm.requests.post", fake_post)
    assert LLMClient(PROVIDER_GROQ, "k").ping() == "ok"


def test_http_errors_are_friendly_and_hide_key(monkeypatch):
    def fake_post(url, headers, json, timeout):
        return FakeResponse(401, {"error": {"message": "API key secret-key is invalid"}})

    monkeypatch.setattr("planner.llm.requests.post", fake_post)
    with pytest.raises(LLMError) as err:
        LLMClient(PROVIDER_GEMINI, "secret-key").ping()
    assert "invalid API key" in str(err.value) and "secret-key" not in str(err.value)
