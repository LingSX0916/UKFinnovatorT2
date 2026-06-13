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


def scan_advert(advert_text: str, promoter: str = "", context: str = "") -> dict:
    """Analyse a financial promotion against FCA.md and return the JSON verdict.

    `promoter` and `context` are optional complaint metadata. They are passed to
    the model as background only — the system prompt instructs it to quote
    evidence solely from the advert, so highlighted spans still match the advert.
    """
    user_content = advert_text
    extra = []
    if promoter:
        extra.append(f'Promoter named in the complaint: "{promoter}".')
    if context:
        extra.append(f"Complaint context: {context}")
    if extra:
        user_content += (
            "\n\n---\nADDITIONAL CONTEXT (background only — do NOT quote this "
            "section in any 'evidence' field; quote only from the advert above):\n"
            + "\n".join(extra)
        )

    response = _get_client().chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _load_rules()},
            {"role": "user", "content": user_content},
        ],
        max_tokens=2048,
    )
    return json.loads(response.choices[0].message.content)
