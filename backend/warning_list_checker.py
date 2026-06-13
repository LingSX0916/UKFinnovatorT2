import json
import os

_WARNING_LIST_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "warning_list.json")
_cached_list: list[str] | None = None


def _load() -> list[str]:
    global _cached_list
    if _cached_list is None:
        with open(_WARNING_LIST_PATH, encoding="utf-8") as f:
            _cached_list = json.load(f)
    return _cached_list


def check_warning_list(named_firms: list[str], named_people: list[str] | None = None) -> list[str]:
    """Return any names that fuzzy-match an entry on the warning list."""
    entries = _load()
    hits = []
    candidates = list(named_firms or []) + list(named_people or [])
    for candidate in candidates:
        candidate_lower = candidate.lower()
        for entry in entries:
            entry_lower = entry.lower()
            if entry_lower in candidate_lower or candidate_lower in entry_lower:
                hits.append(candidate)
                break
    return hits


def find_warning_list_matches(*texts: str) -> list[str]:
    """Return Warning List *entries* that appear in any of the given free-text
    blobs (advert copy, promoter name, …). Independent of the model's output
    schema — we check the inputs we control. Case-insensitive, deduplicated."""
    blob = " \n ".join(t for t in texts if t).lower()
    if not blob.strip():
        return []
    hits = []
    for entry in _load():
        if entry.lower() in blob and entry not in hits:
            hits.append(entry)
    return hits
