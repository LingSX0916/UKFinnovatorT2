import os
import json
import anthropic
from backend.rules_prompt import RULES_SYSTEM_PROMPT

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def scan_advert(advert_text: str) -> dict:
    message = _get_client().messages.create(
        model="claude-opus-4-8",
        max_tokens=2048,
        system=RULES_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": advert_text}],
    )
    raw = message.content[0].text.strip()

    # Strip markdown code fences if the model wraps the JSON
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)
