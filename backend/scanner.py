import json
import os

from openai import OpenAI

from backend.rules_prompt import RULES_SYSTEM_PROMPT

# ---------------------------------------------------------------------------
# LLM client — configured entirely from environment variables.
# Set these in your .env file:
#
#   LLM_API_KEY   — your API key (required)
#   LLM_BASE_URL  — base URL for OpenAI-compatible APIs, e.g.
#                     http://localhost:11434/v1  (Ollama)
#                     https://api.groq.com/openai/v1  (Groq)
#                     https://api.together.xyz/v1      (Together AI)
#                   Leave unset to use the default OpenAI endpoint.
#   LLM_MODEL     — model name as expected by the API, e.g.
#                     gpt-4o, llama3.2, qwen2.5-vl-7b, mistral-large
# ---------------------------------------------------------------------------

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.environ["LLM_API_KEY"],
            base_url=os.environ.get("LLM_BASE_URL"),  # None → default OpenAI endpoint
        )
    return _client


def scan_advert(advert_text: str) -> dict:
    model = os.environ.get("LLM_MODEL", "gpt-4o")

    response = _get_client().chat.completions.create(
        model=model,
        max_tokens=2048,
        messages=[
            {"role": "system", "content": RULES_SYSTEM_PROMPT},
            {"role": "user", "content": advert_text},
        ],
    )
    raw = response.choices[0].message.content.strip()

    # Strip markdown code fences if the model wraps the JSON
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)
