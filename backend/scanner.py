import json
import os
from pathlib import Path
from openai import OpenAI

_client = None
_FCA_MD = Path(__file__).parent.parent / "FCA.md"

# Explicit instruction prepended to the FCA.md rulebook to form the system prompt.
# It pins the method, the output contract (FCA.md section 10) and the evidence rule.
SYSTEM_INSTRUCTION = """You are the FCA Financial Promotions Triage model. Assess the financial promotion supplied by the user — which may be text, an image, or both — strictly against the RULEBOOK below.

Method (follow the rulebook's "Reading order for the model"):
1. Identify the product type (crypto, P2P, NRRS, LTAF, mainstream investment, or unknown).
2. Identify the communicator status (authorised, approved by a named firm, or unauthorised).
3. Run the Warning List check.
4. Evaluate every rule R1 to R17, recording for each: triggered (true/false), severity, the exact evidence phrase, and the provision.
5. Aggregate to one overall verdict using the rulebook's decision logic (a Warning List hit or any RED rule -> RED; else any AMBER rule -> AMBER; else GREEN).

Output contract:
- Return ONLY a single JSON object in EXACTLY the shape given in the rulebook's "Output schema the model returns" (section 10): overall_verdict, summary, warning_list_hit, product_type, communicator_status, and a rules[] array whose items have rule_id, name, triggered, severity, provision, evidence, explanation, suggested_fix.
- Include a rules[] entry for every rule that is TRIGGERED. "evidence" MUST be the exact offending phrase, quoted verbatim from the advert (for an image, the exact text visible in it). No verdict without evidence.
- If an image is supplied, first read ALL of its text and visual elements — headline, body copy, small print, on-screen overlays and captions — then judge.
- Do not invent breaches. If the promotion is compliant, return overall_verdict GREEN with no triggered rules.

RULEBOOK (FCA.md) follows.
============================================================
"""


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        # max_retries rides out transient 429 TPM rate-limits (the board fires a
        # few scans on load); the SDK backs off and retries before we fall back.
        _client = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            max_retries=int(os.environ.get("OPENAI_MAX_RETRIES", "4")),
            timeout=90,
        )
    return _client


def _load_rules() -> str:
    return SYSTEM_INSTRUCTION + _FCA_MD.read_text(encoding="utf-8")


def scan_advert(advert_text: str = "", promoter: str = "", context: str = "",
                image_data_url: str | None = None) -> dict:
    """Analyse a financial promotion (text and/or image) against FCA.md.

    If `image_data_url` (a data: URL) is given, the vision-capable model reads the
    advert from the image. `promoter` and `context` are background only — the
    system prompt tells the model to quote evidence from the advert itself.
    """
    blocks = []
    if image_data_url:
        blocks.append(
            "The reported financial promotion is the attached image. Read every piece "
            "of text and every visual element in it (headline, body copy, small print, "
            "on-screen overlays, captions) and triage it against the rulebook. Quote "
            "evidence verbatim from the text visible in the image."
        )
    if advert_text:
        blocks.append(("Reported advert text:\n" if image_data_url else "") + advert_text)

    extra = []
    if promoter:
        extra.append(f'Promoter named in the complaint: "{promoter}".')
    if context:
        extra.append(f"Complaint context: {context}")
    if extra:
        blocks.append(
            "ADDITIONAL CONTEXT (background only — do NOT quote this section in any "
            "'evidence' field; quote only from the advert above):\n" + "\n".join(extra)
        )

    text = "\n\n".join(blocks) if blocks else "Triage the attached financial promotion."

    if image_data_url:
        user_content = [
            {"type": "text", "text": text},
            {"type": "image_url", "image_url": {"url": image_data_url}},
        ]
    else:
        user_content = text

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
