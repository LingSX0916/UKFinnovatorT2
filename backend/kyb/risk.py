"""FCA / FATF customer risk engine — transparent, rule-based, every factor cited.

Takes the screening results plus the company / officer / PSC / ownership / filing
data and returns a risk assessment whose every factor cites a regulatory provision
and quotes its triggering evidence. Output mirrors FCA.md's per-rule contract so
the two halves of the product feel like one tool.

Pure and deterministic: same inputs -> same assessment, no I/O, no model call.
The rating is advisory — a human compliance officer makes the final call and may
override with a recorded reason (see screening.py / audit_log).
"""
from __future__ import annotations

from . import normalize as N

# ---------------------------------------------------------------------------
# High-risk third countries (FATF + UK MLR 2017 Schedule 3ZA).
#
# TRUTH-OVER-PLAUSIBILITY NOTE: these lists change at each FATF plenary. The set
# below reflects the FATF "call for action" + "increased monitoring" lists and
# the UK Schedule 3ZA as known at the 2026-01 cutoff. It MUST be re-checked
# against the live FATF statement and Schedule 3ZA before any real use — it is a
# starting position, not legal advice. Provenance is stamped so reviewers verify.
# ---------------------------------------------------------------------------
HIGH_RISK_LISTED_DATE = "2026-01"

# Highest risk — FATF call for action (a.k.a. black list).
FATF_CALL_FOR_ACTION = {
    "Iran": ["Iran", "Iran, Islamic Republic of", "Islamic Republic of Iran"],
    "North Korea": ["North Korea", "DPRK", "Korea, Democratic People's Republic of",
                    "Democratic People's Republic of Korea"],
    "Myanmar": ["Myanmar", "Burma"],
}
# Increased monitoring — FATF grey list (representative; refresh before use).
FATF_INCREASED_MONITORING = {
    c: [c] for c in [
        "Algeria", "Angola", "Bulgaria", "Burkina Faso", "Cameroon",
        "Côte d'Ivoire", "Democratic Republic of the Congo", "Haiti", "Kenya",
        "Lebanon", "Mali", "Monaco", "Mozambique", "Namibia", "Nepal", "Nigeria",
        "Philippines", "Senegal", "South Africa", "South Sudan", "Syria",
        "Tanzania", "Venezuela", "Vietnam", "Yemen",
    ]
}


def _build_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for tier, table in (("call_for_action", FATF_CALL_FOR_ACTION),
                        ("increased_monitoring", FATF_INCREASED_MONITORING)):
        for canonical, aliases in table.items():
            for alias in aliases:
                lookup[N.normalize_name(alias)] = f"{canonical}|{tier}"
    return lookup


_COUNTRY_LOOKUP = _build_lookup()


def classify_country(country: str | None) -> tuple[str, str] | None:
    """Return (canonical_country, tier) if high-risk, else None."""
    if not country:
        return None
    hit = _COUNTRY_LOOKUP.get(N.normalize_name(country))
    if not hit:
        return None
    canonical, tier = hit.split("|", 1)
    return (canonical, tier)


# ---------------------------------------------------------------------------
# Provisions (cited verbatim in factor output — see brief Appendix C)
# ---------------------------------------------------------------------------
P_SANCTIONS = "SAMLA 2018; OFSI financial sanctions guidance (asset-freeze prohibitions are strict liability)"
P_OWNERSHIP = "OFSI 'ownership and control' guidance (>50% / control); SAMLA 2018"
P_WARNING = "FSMA 2000 s19 (general prohibition) & s21 (financial promotion); FCA Warning List"
P_JURISDICTION = "MLR 2017 reg 33(3)(a) & Schedule 3ZA; FATF Recommendation 19"
P_OPACITY = "MLR 2017 reg 28(4) (beneficial ownership / 25% threshold); FATF R.24 & R.25; CA 2006 Part 21A (PSC regime)"
P_COMPLEX = "FATF Recommendation 24 (beneficial-ownership transparency)"
P_FILING = "Companies Act 2006 filing duties; JMLSG risk indicators"

# AMBER factor weights and the threshold for an overall AMBER on cumulative risk.
_AMBER_WEIGHTS = {
    "SANCTIONS_POSSIBLE": 0.6,
    "WARNING_LIST_POSSIBLE": 0.6,
    "HIGH_RISK_JURISDICTION": 0.5,
    "BENEFICIAL_OWNERSHIP_OPACITY": 0.4,
    "COMPLEX_STRUCTURE": 0.3,
    "FILING_RISK": 0.3,
}
# Factors that escalate the company to AMBER on their own (a single high-signal
# indicator -> Enhanced Due Diligence), independent of the cumulative-weight path.
_HIGH_FACTORS = {"HIGH_RISK_JURISDICTION", "SANCTIONS_POSSIBLE", "WARNING_LIST_POSSIBLE"}
_AMBER_THRESHOLD = 0.6


def _factor(code, label, triggered, severity, weight, evidence, provision, confidence):
    return {
        "code": code, "label": label, "triggered": bool(triggered),
        "severity": severity, "weight": weight, "evidence": evidence,
        "provision": provision, "confidence": confidence,
    }


def assess_risk(
    *,
    company_number: str,
    company: dict | None = None,
    officers: list[dict] | None = None,
    pscs: list[dict] | None = None,
    screening_matches: list[dict] | None = None,
    warning_hits: list | None = None,
    sanctioned_controllers: list[dict] | None = None,
    ownership: dict | None = None,
    filing_flags: list[dict] | None = None,
    subjects_screened: int = 0,
) -> dict:
    """Produce the company's FCA/FATF risk assessment.

    `screening_matches` are match dicts (matching.Match.to_dict + an optional
    `decision`). `sanctioned_controllers` are graph nodes that are a RED sanctions
    match AND control >50% of the company. `filing_flags` come from the filing
    analysis. Everything is optional so partial data still yields an assessment.
    """
    company = company or {}
    officers = officers or []
    pscs = pscs or []
    screening_matches = screening_matches or []
    warning_hits = warning_hits or []
    sanctioned_controllers = sanctioned_controllers or []
    ownership = ownership or {}
    filing_flags = filing_flags or []

    factors: list[dict] = []

    # --- live matches partition -------------------------------------------------
    def _active(m):
        return m.get("decision") != "dismissed"

    sanctions_red = [m for m in screening_matches
                     if m.get("list") == "UK_SANCTIONS" and m.get("verdict") == "RED" and _active(m)]
    sanctions_amber = [m for m in screening_matches
                       if m.get("list") == "UK_SANCTIONS" and m.get("verdict") == "AMBER" and _active(m)]
    warning_red = [m for m in screening_matches
                   if m.get("list") == "FCA_WARNING" and m.get("verdict") == "RED" and _active(m)]
    warning_amber = [m for m in screening_matches
                     if m.get("list") == "FCA_WARNING" and m.get("verdict") == "AMBER" and _active(m)]

    # --- RED factors ------------------------------------------------------------
    if sanctions_red:
        ev = "; ".join(
            f"{m.get('subject_name')} ({m.get('subject_type')}) -> {m.get('matched_designation_id')} "
            f"'{m.get('matched_name')}' [{m.get('regime_name')}], name_score "
            f"{m.get('matched_fields', {}).get('name_score')}"
            for m in sanctions_red[:5]
        )
        factors.append(_factor(
            "SANCTIONS_MATCH", "Subject matches the UK Sanctions List", True, "RED", 1.0,
            ev, P_SANCTIONS,
            "high" if any(m.get("decision") == "confirmed" for m in sanctions_red) else "medium"))
    else:
        factors.append(_factor("SANCTIONS_MATCH", "Subject matches the UK Sanctions List",
                               False, "RED", 1.0, "No RED sanctions match on any screened subject.",
                               P_SANCTIONS, "high"))

    if sanctioned_controllers:
        ev = "; ".join(
            f"{c.get('name')} ({c.get('ownership_band') or str(c.get('effective_pct')) + '%'}) "
            f"matches {c.get('designation_id')}"
            for c in sanctioned_controllers[:5]
        )
        factors.append(_factor(
            "OWNERSHIP_AND_CONTROL", "Company controlled by a designated person", True, "RED", 1.0,
            ev + " — the company is itself caught by the OFSI ownership & control rule even if not separately listed.",
            P_OWNERSHIP, "high"))

    if warning_hits or warning_red:
        names = list(dict.fromkeys(list(warning_hits) + [m.get("matched_name") for m in warning_red]))
        factors.append(_factor(
            "WARNING_LIST_MATCH", "Company / officer / domain on the FCA Warning List", True, "RED", 1.0,
            "Matched FCA Warning List entries: " + ", ".join(str(n) for n in names if n),
            P_WARNING, "high"))

    # --- AMBER factors ----------------------------------------------------------
    if sanctions_amber:
        ev = "; ".join(
            f"{m.get('subject_name')} ~ {m.get('matched_designation_id')} '{m.get('matched_name')}' "
            f"(name_score {m.get('matched_fields', {}).get('name_score')})"
            for m in sanctions_amber[:5]
        )
        factors.append(_factor(
            "SANCTIONS_POSSIBLE", "Possible (unconfirmed) UK Sanctions List match", True, "AMBER",
            _AMBER_WEIGHTS["SANCTIONS_POSSIBLE"], ev, P_SANCTIONS, "medium"))

    if warning_amber:
        ev = "; ".join(f"{m.get('subject_name')} ~ '{m.get('matched_name')}' "
                       f"(clone-style near-match, score {m.get('score')})"
                       for m in warning_amber[:5])
        factors.append(_factor(
            "WARNING_LIST_POSSIBLE", "Possible FCA Warning List clone near-match", True, "AMBER",
            _AMBER_WEIGHTS["WARNING_LIST_POSSIBLE"], ev, P_WARNING, "medium"))

    jur_hits = _jurisdiction_hits(company, officers)
    if jur_hits:
        factors.append(_factor(
            "HIGH_RISK_JURISDICTION", "Nexus to a high-risk third country", True, "AMBER",
            _AMBER_WEIGHTS["HIGH_RISK_JURISDICTION"],
            "; ".join(jur_hits) + f" (FATF/Sch.3ZA as at {HIGH_RISK_LISTED_DATE} — verify against live lists).",
            P_JURISDICTION, "medium"))

    opacity = _ownership_opacity(pscs)
    if opacity:
        factors.append(_factor(
            "BENEFICIAL_OWNERSHIP_OPACITY", "Beneficial ownership is opaque", True, "AMBER",
            _AMBER_WEIGHTS["BENEFICIAL_OWNERSHIP_OPACITY"], opacity, P_OPACITY, "medium"))

    complexity = _structure_complexity(ownership)
    if complexity:
        factors.append(_factor(
            "COMPLEX_STRUCTURE", "Complex / multi-layer ownership structure", True, "AMBER",
            _AMBER_WEIGHTS["COMPLEX_STRUCTURE"], complexity, P_COMPLEX, "medium"))

    if filing_flags:
        ev = "; ".join(f.get("evidence") or f.get("label") or str(f) for f in filing_flags[:6])
        factors.append(_factor(
            "FILING_RISK", "Adverse filing behaviour", True, "AMBER",
            _AMBER_WEIGHTS["FILING_RISK"], ev, P_FILING, "medium"))

    # --- aggregation (deterministic precedence) ---------------------------------
    triggered = [f for f in factors if f["triggered"]]
    red_triggered = [f for f in triggered if f["severity"] == "RED"]
    amber_triggered = [f for f in triggered if f["severity"] == "AMBER"]
    amber_weight = sum(f["weight"] for f in amber_triggered)
    any_high = any(f["code"] in _HIGH_FACTORS for f in amber_triggered)

    if red_triggered:
        rating, band = "RED", "Prohibited / Enhanced Due Diligence"
        action = ("Do not proceed. Potential asset-freeze breach / unauthorised firm. "
                  "Consider an OFSI report and a SAR to the NCA. This is guidance, not "
                  "legal advice — a human compliance officer decides.")
        score = max(85, 60 + 10 * len(red_triggered))
    elif amber_weight >= _AMBER_THRESHOLD or any_high:
        rating, band = "AMBER", "High risk / Enhanced Due Diligence"
        action = "Apply Enhanced Due Diligence before onboarding; obtain and verify beneficial ownership."
        score = min(80, 45 + int(amber_weight * 30))
    else:
        rating, band = "GREEN", "Standard / Simplified Due Diligence"
        action = "Standard Due Diligence; no elevated risk indicators found."
        score = min(20, 5 + int(amber_weight * 20))

    sanctions_hit = bool(red_triggered and any(f["code"] in ("SANCTIONS_MATCH", "OWNERSHIP_AND_CONTROL")
                                               for f in red_triggered))
    warning_hit = any(f["code"] == "WARNING_LIST_MATCH" for f in red_triggered)
    citations = sorted({f["provision"] for f in triggered}) or [P_SANCTIONS, P_OPACITY]

    summary = _summary(rating, red_triggered, amber_triggered, subjects_screened)

    return {
        "company_number": company_number,
        "overall_rating": rating,
        "fca_fatf_band": band,
        "summary": summary,
        "sanctions_hit": sanctions_hit,
        "warning_list_hit": warning_hit,
        "subjects_screened": subjects_screened,
        "required_action": action,
        "score": score,
        "factors": factors,
        "citations": citations,
    }


# --- factor helpers --------------------------------------------------------
def _jurisdiction_hits(company: dict, officers: list[dict]) -> list[str]:
    hits: list[str] = []
    ro = (company.get("registered_office") or {})
    for label, country in (
        ("registered office", ro.get("country")),
        ("jurisdiction", company.get("jurisdiction")),
    ):
        c = classify_country(country)
        if c:
            hits.append(f"{label}: {c[0]} ({c[1].replace('_', ' ')})")
    for off in officers:
        for label, key in (("officer nationality", "nationality"),
                           ("officer residence", "country_of_residence")):
            c = classify_country(off.get(key))
            if c:
                hits.append(f"{off.get('name', 'officer')} {label}: {c[0]} ({c[1].replace('_', ' ')})")
    # dedupe, preserve order
    seen, out = set(), []
    for h in hits:
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out


def _ownership_opacity(pscs: list[dict]) -> str | None:
    if not pscs:
        return ("No person with significant control is declared for the company "
                "(no PSC on record).")

    def _is_statement(p):
        return "statement" in (p.get("kind") or "").lower() or \
               "no individual" in (p.get("name", "") or "").lower()

    active = [p for p in pscs if not p.get("ceased_on")]
    real_active = [p for p in active if not _is_statement(p)]
    statements = [p for p in pscs if _is_statement(p)]
    if statements and not real_active:
        return ("A PSC statement asserts no individual / RLE has significant control, "
                "so the beneficial owner is undeclared.")
    if not real_active:
        return "All declared PSCs have ceased and none has been replaced."
    return None


def _structure_complexity(ownership: dict) -> str | None:
    max_depth = ownership.get("max_depth", 0)
    foreign = ownership.get("foreign_rle", False)
    if max_depth and max_depth >= 2:
        return (f"Ownership resolves through {max_depth} layers of corporate control"
                + (" including a foreign registered legal entity." if foreign else "."))
    if foreign:
        return "Ownership runs through a foreign registered legal entity (RLE)."
    return None


def _summary(rating, red, amber, n) -> str:
    if rating == "RED":
        lead = red[0]["label"].lower()
        return (f"RED: {lead}. {len(red)} prohibitive factor(s) across {n} screened "
                f"subject(s). Decline and report; human review required.")
    if rating == "AMBER":
        labels = ", ".join(f["label"].lower() for f in amber[:3])
        return (f"AMBER: elevated money-laundering risk — {labels}. Enhanced Due "
                f"Diligence required across {n} screened subject(s).")
    return (f"GREEN: no elevated sanctions, ownership or filing risk found across "
            f"{n} screened subject(s). Standard Due Diligence.")
