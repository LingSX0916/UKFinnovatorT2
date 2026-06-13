import json
import os
from pathlib import Path
from openai import OpenAI

_client = None
_FCA_MD = Path(__file__).parent.parent / "FCA.md"


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


def _load_rules() -> str:
    return _FCA_MD.read_text(encoding="utf-8")


def scan_advert(advert_text: str) -> dict:
    response = _get_client().chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _load_rules()},
            {"role": "user", "content": advert_text},
        ],
        max_tokens=2048,
    )
    return json.loads(response.choices[0].message.content)
