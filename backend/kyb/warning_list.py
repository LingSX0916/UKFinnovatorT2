"""FCA Warning List screening for KYB subjects.

Reuses the repo's existing `data/warning_list.json` (the flat list of fictional
unauthorised firms the promotions engine already cites) as the firm source, and
optionally layers a richer `data/warning_list_kyb.json` so it can also match on
named individuals and domains — clone firms deliberately mimic authorised names
(FCA.md §8). There is no second, competing Warning List path: this loader is the
single KYB-side view over the same data.

A Warning List hit forces RED (FCA.md §8 / §9). Returns matches in the same shape
as the sanctions matcher so the UI renders both lists with one component.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

from rapidfuzz import fuzz

from . import normalize as N

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
_FLAT_PATH = os.path.join(_DATA_DIR, "warning_list.json")
_KYB_PATH = os.path.join(_DATA_DIR, "warning_list_kyb.json")

NEAR_MATCH = 0.90   # rapidfuzz token-set >= this but not exact -> AMBER (clone-style)


@dataclass
class WarningEntry:
    entry_id: str
    entry_type: str            # firm | individual | domain
    name: str
    normalized_name: str
    domain: str | None = None
    details: dict | None = None
    source: str = "fca_warning_list"


def _norm_domain(d: str) -> str:
    d = (d or "").strip().lower()
    for pre in ("https://", "http://", "www."):
        if d.startswith(pre):
            d = d[len(pre):]
    return d.split("/")[0]


def load_entries() -> list[WarningEntry]:
    entries: list[WarningEntry] = []
    # 1) the existing flat firm-name list (back-compatible)
    try:
        with open(_FLAT_PATH, encoding="utf-8") as f:
            for i, name in enumerate(json.load(f)):
                if isinstance(name, str) and name.strip():
                    entries.append(WarningEntry(
                        entry_id=f"WL-FIRM-{i}", entry_type="firm", name=name,
                        normalized_name=N.normalize_name(name, drop_corp_suffixes=True)))
    except FileNotFoundError:
        pass
    # 2) optional richer KYB entries (firm / individual / domain)
    try:
        with open(_KYB_PATH, encoding="utf-8") as f:
            for i, row in enumerate(json.load(f)):
                etype = (row.get("entry_type") or "firm").lower()
                name = row.get("name") or row.get("domain") or ""
                entries.append(WarningEntry(
                    entry_id=row.get("id") or f"WL-KYB-{i}",
                    entry_type=etype,
                    name=name,
                    normalized_name=N.normalize_name(
                        name, drop_corp_suffixes=(etype != "individual")),
                    domain=_norm_domain(row["domain"]) if row.get("domain") else None,
                    details=row.get("details"),
                    source=row.get("source", "fca_warning_list_kyb"),
                ))
    except FileNotFoundError:
        pass
    return entries


class WarningList:
    """In-memory FCA Warning List index for screening KYB subjects."""

    def __init__(self, entries: list[WarningEntry] | None = None):
        self.entries = entries if entries is not None else load_entries()

    def screen(self, subject) -> list[dict]:
        """Screen a matching.Subject against the Warning List.

        Matches a subject name (firm or individual) and any domains carried in
        the subject's identifiers. Exact normalized match -> RED; near-match (a
        clone deliberately close to a real name) -> AMBER.
        """
        subj_norm = N.normalize_name(
            subject.name,
            drop_corp_suffixes=(subject.subject_type.lower() in {"company", "entity", "corporate-entity", "legal-person"}))
        subj_domains = {_norm_domain(x) for x in subject.identifiers if "." in str(x)}

        out: list[dict] = []
        for e in self.entries:
            verdict = score = None
            field = None
            if e.entry_type == "domain" and e.domain and e.domain in subj_domains:
                verdict, score, field = "RED", 1.0, "domain"
            elif e.domain and e.domain in subj_domains:
                verdict, score, field = "RED", 1.0, "domain"
            elif subj_norm and e.normalized_name:
                if subj_norm == e.normalized_name:
                    verdict, score, field = "RED", 1.0, "name"
                else:
                    s = fuzz.token_set_ratio(subj_norm, e.normalized_name) / 100.0
                    # require shared distinctive content, not just a common word
                    if s >= NEAR_MATCH and _shares_distinctive_token(subj_norm, e.normalized_name):
                        verdict, score, field = "AMBER", s, "name~near"
            if verdict:
                out.append({
                    "subject_ref": subject.ref,
                    "subject_type": subject.subject_type,
                    "subject_name": subject.name,
                    "list": "FCA_WARNING",
                    "matched_designation_id": e.entry_id,
                    "matched_name": e.name,
                    "score": round(score, 4),
                    "verdict": verdict,
                    "matched_fields": {"matched_on": field, "name_score": round(score, 4)},
                    "evidence": {
                        "entry_type": e.entry_type, "source": e.source,
                        "domain": e.domain, "details": e.details,
                        "note": "FCA Warning List hit forces RED (FCA.md §8/§9); "
                                "clone firms mimic authorised names — confirm on the live FCA register.",
                    },
                })
        return sorted(out, key=lambda m: m["score"], reverse=True)


def _shares_distinctive_token(a: str, b: str) -> bool:
    """True if the two names share a token longer than 3 chars — stops a near-match
    AMBER firing on nothing but 'LTD'/'THE'/'UK'."""
    short = {t for t in a.split(" ") if len(t) > 3}
    return bool(short & {t for t in b.split(" ") if len(t) > 3})
