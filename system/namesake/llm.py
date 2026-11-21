"""OpenRouter second opinion only. Never decides. No key → reader-only path."""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


class LLMClient:
    """Bounded, deterministic-ish second opinions via OpenRouter."""

    def __init__(self) -> None:
        self.api_key = os.environ.get("OPENROUTER_API_KEY") or ""
        self.enabled = bool(self.api_key.strip())
        self.cache: Dict[str, Any] = {}
        self.model = os.environ.get("NAMESAKE_MODEL", "qwen/qwen3-32b")
        self.calls = 0
        self.failures = 0

    def second_opinion(self, text: str) -> Optional[Dict[str, Any]]:
        """Return typed facts with verbatim quotes, or None if unavailable/disagree path."""
        if not self.enabled:
            return None
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if key in self.cache:
            return self.cache[key]
        try:
            result = self._call(text)
            self.cache[key] = result
            self.calls += 1
            return result
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError):
            self.failures += 1
            self.cache[key] = None
            return None

    def _call(self, text: str) -> Dict[str, Any]:
        body = {
            "model": self.model,
            "temperature": 0,
            "seed": 0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "facts",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "facts": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "kind": {"type": "string"},
                                        "value": {"type": "string"},
                                        "quote": {"type": "string"},
                                        "polarity": {"type": "string"},
                                    },
                                    "required": ["kind", "value", "quote", "polarity"],
                                    "additionalProperties": False,
                                },
                            }
                        },
                        "required": ["facts"],
                        "additionalProperties": False,
                    },
                },
            },
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Extract typed identity facts from the text. "
                        "Each fact needs a verbatim quote from the text. "
                        "Do not decide same-person questions."
                    ),
                },
                {"role": "user", "content": text[:4000]},
            ],
        }
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        content = payload["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        # Re-validate quotes are substrings
        facts: List[Dict[str, Any]] = []
        for fact in parsed.get("facts") or []:
            quote = fact.get("quote") or ""
            if quote and quote in text:
                facts.append(fact)
        return {"facts": facts}


def reconcile_with_reader(
    reader_value: Optional[str], llm_payload: Optional[Dict[str, Any]], kind: str
) -> str:
    """Return C if reader and LLM agree (or no LLM); U on disagreement."""
    if llm_payload is None:
        return "C"  # reader-only path; caller marks which rules are safe
    for fact in llm_payload.get("facts") or []:
        if fact.get("kind") == kind:
            if reader_value and str(reader_value).lower() in str(fact.get("value") or "").lower():
                return "C"
            return "U"
    return "C"
