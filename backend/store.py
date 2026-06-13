"""Supabase persistence for triaged complaints.

Server-side only. Reads SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY from the
environment — the service-role key bypasses RLS, so it must NEVER reach the
browser or be committed. The frontend talks to Flask (/complaints); Flask is
the only thing that talks to Supabase.

If the env vars are absent the app runs in demo-only mode (no persistence),
so local dev works without any Supabase setup.
"""
import os

TABLE = "complaints"
_client = None


def enabled() -> bool:
    return bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))


def _get_client():
    global _client
    if _client is None:
        from supabase import create_client  # lazy: optional dependency
        _client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_ROLE_KEY"],
        )
    return _client


def list_complaints() -> list[dict]:
    """Return persisted complaint cards (the full UI payload), newest first."""
    res = _get_client().table(TABLE).select("payload").order("created_at", desc=True).execute()
    return [row["payload"] for row in (res.data or []) if row.get("payload")]


def save_complaint(card: dict) -> None:
    """Upsert a triaged complaint card by its ref."""
    analysis = card.get("analysis") or {}
    row = {
        "ref": card.get("ref"),
        "promoter": card.get("promoter"),
        "rag": analysis.get("rag"),
        "payload": card,
    }
    _get_client().table(TABLE).upsert(row, on_conflict="ref").execute()
