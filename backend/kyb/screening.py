"""Screening orchestrator — the engine behind the "Run sanction check" button.

Loads a company's officers, PSCs and ownership graph, screens every subject (the
company itself + every officer + every PSC/UBO, including indirect owners) against
the UK Sanctions List and the FCA Warning List, runs the FCA/FATF risk engine, and
returns one structured, persisted, fully-cited result.

The heavy UKSL index is loaded once (lazily) and cached — with an on-disk pickle
keyed by the file's SHA so server restarts are fast. If no UKSL file is configured
the index is empty and screening degrades to Warning-List-only rather than failing.
"""
from __future__ import annotations

import datetime
import os
import pickle
import uuid
from pathlib import Path

from . import normalize as N
from . import risk as risk_engine
from . import uksl
from .graph import build_ownership_graph
from .matching import Subject, SanctionsIndex, build_index
from .warning_list import WarningList

_ENTITY_TYPES = {"company", "entity", "corporate-entity", "legal-person"}

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_UKSL_CANDIDATES = [
    _REPO_ROOT / "inputs" / "UK-Sanctions-List.xml",
    _REPO_ROOT / "tests" / "kyb" / "fixtures" / "uksl_sample.xml",
]

_INDEX: SanctionsIndex | None = None
_INDEX_SOURCE: str | None = None


def _resolve_uksl_path() -> Path | None:
    env = os.environ.get("UKSL_XML_PATH")
    if env and Path(env).exists():
        return Path(env)
    for cand in _DEFAULT_UKSL_CANDIDATES:
        if cand.exists():
            return cand
    return None


def _cached_designations(path: Path) -> list[uksl.Designation]:
    """Parse the UKSL file, caching the parsed objects to a pickle keyed by SHA so
    repeated server starts don't re-parse the 21 MB file."""
    sha = uksl.file_sha256(str(path))[:16]
    cache = Path(os.environ.get("TEMP", "/tmp")) / f"uksl_{sha}.pkl"
    if cache.exists():
        try:
            with open(cache, "rb") as f:
                return pickle.load(f)
        except Exception:
            pass
    desigs = uksl.load_uksl(str(path))
    try:
        with open(cache, "wb") as f:
            pickle.dump(desigs, f)
    except Exception:
        pass
    return desigs


def get_index(force: bool = False) -> SanctionsIndex:
    global _INDEX, _INDEX_SOURCE
    if _INDEX is not None and not force:
        return _INDEX
    path = _resolve_uksl_path()
    if path is None:
        _INDEX, _INDEX_SOURCE = build_index([]), None
        return _INDEX
    _INDEX = build_index(_cached_designations(path))
    _INDEX_SOURCE = str(path)
    return _INDEX


def index_info() -> dict:
    idx = get_index()
    return {"source": _INDEX_SOURCE, "designations": len(idx.designations)}


# ---------------------------------------------------------------------------
# Filing-derived risk flags
# ---------------------------------------------------------------------------
def analyze_filings(profile: dict, filings: list[dict], as_of: str | None = None) -> list[dict]:
    flags: list[dict] = []
    if profile.get("accounts_overdue"):
        nd = (profile.get("accounts") or {}).get("next_due")
        flags.append({"code": "ACCOUNTS_OVERDUE", "label": "Accounts overdue",
                      "evidence": f"Annual accounts overdue (next due {nd})."})
    if profile.get("confirmation_overdue"):
        nd = (profile.get("confirmation_statement") or {}).get("next_due")
        flags.append({"code": "CS_OVERDUE", "label": "Confirmation statement overdue",
                      "evidence": f"Confirmation statement overdue (next due {nd})."})

    status = (profile.get("status") or "").lower()
    if "strike" in status or "liquidation" in status or "dissolved" in status:
        flags.append({"code": "STRIKE_OFF", "label": "Adverse company status",
                      "evidence": f"Company status is '{profile.get('status')}'."})

    for f in filings:
        desc = (f.get("description") or "").lower()
        ftype = (f.get("type") or "").lower()
        if "gaz" in (f.get("category") or "").lower() or "strike-off" in ftype or "first gazette" in desc:
            flags.append({"code": "GAZETTE_STRIKE_OFF", "label": "Strike-off / gazette notice",
                          "evidence": f"{f.get('date')}: {f.get('description') or f.get('type')}"})
            break

    # officer / registered-office churn
    officer_changes = sum(1 for f in filings if (f.get("category") or "").lower() == "officers")
    if officer_changes >= 4:
        flags.append({"code": "OFFICER_CHURN", "label": "High officer churn",
                      "evidence": f"{officer_changes} officer-change filings on record."})
    addr_changes = sum(1 for f in filings
                       if "registered office" in (f.get("description") or "").lower())
    if addr_changes >= 3:
        flags.append({"code": "ADDRESS_CHURN", "label": "Frequent registered-office changes",
                      "evidence": f"{addr_changes} registered-office changes on record."})

    # very recent incorporation
    doc = profile.get("date_of_creation")
    if as_of and doc:
        try:
            d0 = datetime.date.fromisoformat(doc)
            d1 = datetime.date.fromisoformat(as_of)
            if 0 <= (d1 - d0).days <= 180 and filings:
                flags.append({"code": "RECENT_INCORPORATION",
                              "label": "Very recent incorporation with activity",
                              "evidence": f"Incorporated {doc} ({(d1 - d0).days} days ago) with filing activity already."})
        except (ValueError, TypeError):
            pass  # malformed/non-string date -> skip the recency flag, never 500
    return flags


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def _company_subject(profile: dict, number: str) -> Subject:
    return Subject(
        name=profile.get("name") or number,
        subject_type="company",
        ref=f"company:{number}",
        identifiers=[number],
        country=(profile.get("registered_office") or {}).get("country"),
    )


def _officer_subject(o: dict) -> Subject:
    return Subject(
        name=o.get("name") or "",
        subject_type="officer",
        ref=o.get("id"),
        dob_year=o.get("dob_year"),
        nationalities=[o["nationality"]] if o.get("nationality") else [],
        country=o.get("country_of_residence"),
    )


def screen_company(client, company_number: str, *, run_by: str | None = None,
                   as_of: str | None = None, store=None) -> dict:
    profile = client.get_profile(company_number)
    if not profile:
        return {"error": f"company {company_number} not found", "company_number": company_number}

    officers = client.get_officers(company_number)
    pscs = client.get_pscs(company_number)
    filings = client.get_filing_history(company_number)
    graph = build_ownership_graph(client, company_number)

    # Build the subject set: company + officers + every owner node (incl. indirect)
    subjects: list[Subject] = [_company_subject(profile, company_number)]
    subjects += [_officer_subject(o) for o in officers if o.get("name")]
    subjects += graph["subjects"]

    index = get_index()
    wl = WarningList()
    node_by_ref = {n["id"]: n for n in graph["nodes"]}

    # A person can appear as BOTH an officer ("SMITH, Jane") and a PSC ("Jane
    # Smith"); we screen each distinct identity once (token-sorted normalized name
    # + DOB) but still attach the result to every graph node it maps to, so the
    # UBO node is coloured and the ownership-and-control rule can't miss a director.
    def _ident_key(s: Subject) -> tuple:
        cls = "company" if s.subject_type.lower() in _ENTITY_TYPES else "person"
        toks = sorted(N.normalize_tokens(s.name or "", drop_honorifics=(cls == "person")))
        return (cls, " ".join(toks), s.dob_year or "")

    def _screen_one(s: Subject) -> dict:
        sanc = [m.to_dict() for m in index.screen(s)] if index.designations else []
        warn = wl.screen(s)
        matches = sanc + warn
        for m in matches:
            m["id"] = str(uuid.uuid4())  # stable id so the UI can confirm/dismiss it
        return {"matches": matches, "verdict": _worst([m["verdict"] for m in matches])}

    screened: dict[tuple, dict] = {}
    all_matches: list[dict] = []
    subjects_status: list[dict] = []
    for s in subjects:
        k = _ident_key(s)
        if k not in screened:
            res = screened[k] = _screen_one(s)
            all_matches.extend(res["matches"])
            subjects_status.append({
                "subject_ref": s.ref, "subject_type": s.subject_type,
                "subject_name": s.name, "verdict": res["verdict"],
                "match_count": len(res["matches"]),
                "top_match": res["matches"][0] if res["matches"] else None,
            })
        res = screened[k]
        if s.ref in node_by_ref:
            node_by_ref[s.ref]["screening"] = {
                "verdict": res["verdict"],
                "designation_id": res["matches"][0]["matched_designation_id"] if res["matches"] else None,
            }
    subjects_screened = len(screened)

    # OFSI ownership & control: aggregate a designated owner's effective holding
    # ACROSS all chains (two 30% routes = 60% caught), then apply the >50% test.
    by_designation: dict[str, dict] = {}
    for n in graph["nodes"]:
        scr = n.get("screening") or {}
        if scr.get("verdict") != "RED":
            continue
        did = scr.get("designation_id") or n["id"]
        agg = by_designation.setdefault(did, {
            "name": n.get("name"), "designation_id": scr.get("designation_id"),
            "eff": 0.0, "control": False, "band": n.get("ownership_band")})
        agg["eff"] += (n.get("effective_pct") or 0)
        agg["control"] = agg["control"] or bool(n.get("is_control"))
    sanctioned_controllers = [
        {"name": a["name"], "designation_id": a["designation_id"],
         "ownership_band": a["band"], "effective_pct": round(a["eff"], 1)}
        for a in by_designation.values() if a["control"] or a["eff"] > 50
    ]

    filing_flags = analyze_filings(profile, filings, as_of=as_of)

    assessment = risk_engine.assess_risk(
        company_number=company_number,
        company=profile,
        officers=officers,
        pscs=pscs,
        screening_matches=all_matches,
        sanctioned_controllers=sanctioned_controllers,
        ownership={"max_depth": graph["max_depth"], "foreign_rle": graph["foreign_rle"]},
        filing_flags=filing_flags,
        subjects_screened=subjects_screened,
    )

    run_id = str(uuid.uuid4())
    result = {
        "run_id": run_id,
        "company_number": company_number,
        "company_name": profile.get("name"),
        "run_by": run_by,
        "run_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "lists_checked": ["UK_SANCTIONS", "FCA_WARNING"],
        "subjects_screened": subjects_screened,
        "overall_verdict": assessment["overall_rating"],
        "matches": [m for m in all_matches if m["verdict"] in ("RED", "AMBER")],
        "subjects_status": subjects_status,
        "risk_assessment": assessment,
        "filing_flags": filing_flags,
        "ownership_graph": graph_public(graph),
        "index_source": index_info(),
    }
    if store is not None:
        try:
            store.save_screening(result)
        except Exception:
            pass
    return result


def graph_public(graph: dict) -> dict:
    """Strip the internal Subject objects before returning the graph to the client."""
    return {k: v for k, v in graph.items() if k != "subjects"}


def _worst(verdicts: list[str]) -> str:
    order = {"RED": 0, "AMBER": 1, "GREEN": 2}
    best = "GREEN"
    for v in verdicts:
        if order.get(v, 3) < order.get(best, 3):
            best = v
    return best


def get_dossier(client, company_number: str) -> dict:
    """Read-only company dossier (profile, officers, PSCs, filings, ownership graph)
    — no screening, for the dossier view before the user hits Run sanction check."""
    profile = client.get_profile(company_number)
    if not profile:
        return {"error": f"company {company_number} not found", "company_number": company_number}
    return {
        "profile": profile,
        "officers": client.get_officers(company_number),
        "psc": client.get_pscs(company_number),
        "filing_history": client.get_filing_history(company_number),
        "ownership_graph": graph_public(build_ownership_graph(client, company_number)),
    }
