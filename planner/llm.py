"""Thin, dependency-free clients for Google Gemini and Groq (REST over ``requests``).

Every call asks the model for strict JSON. Any network, auth or parsing problem is
raised as ``LLMError`` so the UI can fall back to the offline engine gracefully.
"""

from __future__ import annotations

import json
import re

import requests

from .config import DEFAULT_MODELS, PROVIDER_DEMO, PROVIDER_GEMINI, PROVIDER_GROQ

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class LLMError(RuntimeError):
    """Raised when the AI provider cannot return usable JSON."""


def extract_json(text: str) -> dict | list:
    """Parse JSON from a model reply, tolerating code fences or leading prose."""
    if not text or not text.strip():
        raise LLMError("The model returned an empty response.")
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start, end = cleaned.find(open_ch), cleaned.rfind(close_ch)
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start:end + 1])
            except json.JSONDecodeError:
                continue
    raise LLMError("The model response was not valid JSON.")


class LLMClient:
    def __init__(self, provider: str, api_key: str = "", model: str = "", timeout: int = 60):
        self.provider = provider
        self.api_key = (api_key or "").strip()
        self.model = (model or DEFAULT_MODELS.get(provider, "")).strip()
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return self.provider in (PROVIDER_GEMINI, PROVIDER_GROQ) and bool(self.api_key)

    @property
    def label(self) -> str:
        return f"{self.provider} · {self.model}" if self.enabled else PROVIDER_DEMO

    def generate_json(self, system: str, user: str, temperature: float = 0.4) -> dict | list:
        if not self.enabled:
            raise LLMError("No AI provider configured.")
        try:
            if self.provider == PROVIDER_GEMINI:
                text = self._gemini(system, user, temperature)
            else:
                text = self._groq(system, user, temperature)
        except requests.Timeout as exc:
            raise LLMError("The AI provider timed out. Try again or switch to demo mode.") from exc
        except requests.RequestException as exc:
            raise LLMError(f"Network error contacting {self.provider}: {type(exc).__name__}") from exc
        return extract_json(text)

    # -- providers ---------------------------------------------------------
    def _gemini(self, system: str, user: str, temperature: float) -> str:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": temperature, "responseMimeType": "application/json"},
        }
        resp = requests.post(
            GEMINI_URL.format(model=self.model),
            headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
            json=body,
            timeout=self.timeout,
        )
        self._raise_for_status(resp)
        data = resp.json()
        try:
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts)
        except (KeyError, IndexError, TypeError) as exc:
            reason = (data.get("promptFeedback") or {}).get("blockReason") if isinstance(data, dict) else None
            raise LLMError(f"Gemini returned no content{f' ({reason})' if reason else ''}.") from exc

    def _groq(self, system: str, user: str, temperature: float) -> str:
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=body,
            timeout=self.timeout,
        )
        self._raise_for_status(resp)
        try:
            return resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMError("Groq returned an unexpected response shape.") from exc

    def _raise_for_status(self, resp: requests.Response) -> None:
        if resp.status_code < 400:
            return
        hints = {
            400: "bad request – check the model name",
            401: "invalid API key",
            403: "API key not authorised for this model",
            404: "model not found – check the model name",
            429: "rate limit or quota exceeded",
        }
        detail = ""
        try:
            payload = resp.json()
            err = payload.get("error") if isinstance(payload, dict) else None
            if isinstance(err, dict):
                detail = str(err.get("message", ""))[:160]
        except ValueError:
            pass
        if self.api_key:
            detail = detail.replace(self.api_key, "***")
        hint = hints.get(resp.status_code, "provider error")
        raise LLMError(f"{self.provider} HTTP {resp.status_code}: {hint}. {detail}".strip())

    def ping(self) -> str:
        """Cheap connectivity check used by the sidebar 'Test connection' button."""
        reply = self.generate_json(
            "You are a health check. Reply with JSON only.",
            'Return exactly {"status": "ok"}.',
            temperature=0,
        )
        if isinstance(reply, dict) and str(reply.get("status", "")).lower() == "ok":
            return "ok"
        raise LLMError("Unexpected health-check reply.")
