"""Optional Supabase persistence for KYB screening (server-side only).

Follows the repo's existing pattern (backend/store.py): reads SUPABASE_URL +
SUPABASE_SERVICE_ROLE_KEY from the environment; the service-role key bypasses RLS
and must NEVER reach the browser. If those vars are absent the whole module is a
no-op (enabled() == False) and the app runs demo-only — the engines and API still
work, results just aren't persisted.

Tables are created by supabase/migrations/0002_kyb_sanctions.sql. The audit_log
table has INSERT+SELECT policies only, so the trail is tamper-evident.
"""
from __future__ import annotations

import os

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


def save_screening(result: dict) -> None:
    """Persist a screening run: the run row, every match, and the risk assessment."""
    c = _get_client()
    run_id = result["run_id"]
    risk = result.get("risk_assessment", {})
    c.table("screening_run").upsert({
        "id": run_id,
        "company_number": result["company_number"],
        "run_by": result.get("run_by"),
        "run_at": result.get("run_at"),
        "lists_checked": result.get("lists_checked"),
        "overall_verdict": result.get("overall_verdict"),
        "subjects_screened": result.get("subjects_screened"),
        "summary": risk.get("summary"),
    }).execute()

    for m in result.get("matches", []):
        c.table("screening_match").upsert({
            "id": m["id"],
            "run_id": run_id,
            "subject_type": m.get("subject_type"),
            "subject_ref": m.get("subject_ref"),
            "subject_name": m.get("subject_name"),
            "list": m.get("list"),
            "matched_designation_id": m.get("matched_designation_id"),
            "matched_name": m.get("matched_name"),
            "score": m.get("score"),
            "verdict": m.get("verdict"),
            "matched_fields": m.get("matched_fields"),
            "evidence": m.get("evidence"),
            "decision": "pending",
        }).execute()

    c.table("risk_assessment").insert({
        "company_number": result["company_number"],
        "run_id": run_id,
        "overall_rating": risk.get("overall_rating"),
        "score": risk.get("score"),
        "factors": risk.get("factors"),
    }).execute()

    audit(result.get("run_by") or "system", "screening.run", "company",
          result["company_number"], {"run_id": run_id, "verdict": result.get("overall_verdict")})


def record_decision(match_id: str, decision: str, note: str, reviewer: str) -> None:
    """Confirm / dismiss a match with a reviewer note."""
    _get_client().table("screening_match").update({
        "decision": decision,
        "reviewer": reviewer,
        "reviewer_note": note,
        "decided_at": "now()",
    }).eq("id", match_id).execute()


def audit(actor: str, action: str, entity: str, entity_ref: str, payload: dict | None = None) -> None:
    """Append an immutable audit-log row (INSERT-only by policy)."""
    _get_client().table("audit_log").insert({
        "actor": actor, "action": action, "entity": entity,
        "entity_ref": entity_ref, "payload": payload or {},
    }).execute()


# ---------------------------------------------------------------------------
# Sanctions ingestion (idempotent upsert keyed on the UKSL Unique ID)
# ---------------------------------------------------------------------------
def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def upsert_designations(designations, *, source_file: str, file_sha256: str,
                        batch: int = 200) -> int:
    """Upsert UKSL designations + their names/identifiers/dobs/addresses.

    Idempotent on unique_id: the parent row is upserted and its child rows are
    replaced, so re-running the ingest never duplicates. Records one
    sanctions_import provenance row per run.
    """
    c = _get_client()
    ids = [d.unique_id for d in designations]

    # 1) parent rows
    for part in _chunks(designations, batch):
        c.table("sanctions_designation").upsert([{
            "unique_id": d.unique_id,
            "ofsi_group_id": d.ofsi_group_id,
            "un_reference_number": d.un_reference_number,
            "group_type": d.group_type,
            "regime_name": d.regime_name,
            "designation_source": d.designation_source,
            "sanctions_imposed": d.sanctions_imposed,
            "uk_statement_of_reasons": d.uk_statement_of_reasons,
            "other_information": d.other_information,
            "date_designated": d.date_designated,
            "last_updated": d.last_updated,
            "raw": d.raw,
        } for d in part], on_conflict="unique_id").execute()

    # 2) replace child rows for these designations
    for part in _chunks(ids, 50):
        for tbl in ("sanctions_name", "sanctions_identifier", "sanctions_dob",
                    "sanctions_address", "sanctions_attribute"):
            c.table(tbl).delete().in_("designation_id", part).execute()

    names, idents, dobs, addrs, attrs = [], [], [], [], []
    for d in designations:
        for nm in d.names:
            names.append({
                "designation_id": d.unique_id, "name_type": nm.name_type,
                "alias_strength": nm.alias_strength, "full_name": nm.full_name,
                "normalized_name": nm.normalized_name,
            })
        for it in d.identifiers:
            idents.append({
                "designation_id": d.unique_id, "id_type": it.id_type,
                "id_value": it.value, "normalized_value": it.normalized,
                "additional_info": it.additional_info,
            })
        for db in d.dobs:
            dobs.append({"designation_id": d.unique_id, "dob_raw": db.raw,
                         "dob_year": db.year, "dob_month": db.month, "dob_day": db.day})
        for a in d.addresses:
            addrs.append({"designation_id": d.unique_id, "line1": a.get("line1"),
                          "line2": a.get("line2"), "line3": a.get("line3"),
                          "line4": a.get("line4"), "line5": a.get("line5"),
                          "line6": a.get("line6"), "postal_code": a.get("postal_code"),
                          "country": a.get("country")})
        for nat in d.nationalities:
            attrs.append({"designation_id": d.unique_id, "attr_key": "nationality", "attr_value": nat})
        for pos in d.positions:
            attrs.append({"designation_id": d.unique_id, "attr_key": "position", "attr_value": pos})

    for tbl, rows in (("sanctions_name", names), ("sanctions_identifier", idents),
                      ("sanctions_dob", dobs), ("sanctions_address", addrs),
                      ("sanctions_attribute", attrs)):
        for part in _chunks(rows, batch):
            if part:
                c.table(tbl).insert(part).execute()

    c.table("sanctions_import").insert({
        "source_file": source_file, "file_sha256": file_sha256,
        "designation_count": len(designations),
        "notes": "ingested via backend.kyb.ingest_uksl",
    }).execute()
    return len(designations)
