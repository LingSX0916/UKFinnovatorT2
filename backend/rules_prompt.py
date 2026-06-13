from pathlib import Path

_INSTRUCTIONS_FILE = Path(__file__).parent / "instructions.md"

RULES_SYSTEM_PROMPT: str = _INSTRUCTIONS_FILE.read_text(encoding="utf-8")
