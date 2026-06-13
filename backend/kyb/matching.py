"""Regulator-grade, explainable sanctions matching.

Pure functions and an in-memory index — no DB calls inside scoring. Given a
Subject (an officer, a PSC/UBO, or the company itself) and the parsed UKSL
designations, it returns scored, fully-explained matches.

Design, mirroring FCA.md's "no verdict without evidence":
  * Combine metrics, never trust one — name_score is the max of Jaro-Winkler and
    rapidfuzz token-set ratio (handles reordered / missing middle names).
  * Corroborate — DOB, nationality and (decisively) an exact identifier / business
    registration number raise or lower confidence. A DOB that explicitly conflicts
    is treated as dis-confirming evidence and blocks a RED.
  * Triage, never enforce — RED means "likely true match, escalate for a human to
    confirm", never auto-confirm. False-positive guards keep common names out of RED
    unless corroborated.
  * Explain everything — every Match carries its sub-scores, which fields
    corroborated, and the designation's regime + UK Statement of Reasons.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from rapidfuzz import fuzz

from . import normalize as N
from .uksl import Designation

# jellyfish API name moved across versions; accept either.
try:  # pragma: no cover - import wiring
    from jellyfish import jaro_winkler_similarity as _jw
except Exception:  # pragma: no cover
    from jellyfish import jaro_winkler as _jw  # type: ignore
try:  # pragma: no cover
    from jellyfish import metaphone as _metaphone
except Exception:  # pragma: no cover
    def _metaphone(s: str) -> str:  # type: ignore
        return s

# --- Tunable thresholds (documented; the whole verdict rests on these) ---------
RED_NAME_THRESHOLD = 0.93     # likely true match (with corroboration)
AMBER_NAME_THRESHOLD = 0.85   # possible match, needs review
COMMON_TOKEN_DF = 40          # a name token in > this many designations is "common"

# Which UKSL group types a subject is screened against. Individuals (officers,
# PSCs) match Individual designations; the company / corporate PSCs match Entity
# designations. This group gating is itself a major false-positive reducer.
_COMPATIBLE = {
    "individual": {"Individual"},
    "officer": {"Individual"},
    "psc": {"Individual"},
    "person": {"Individual"},
    "entity": {"Entity"},
    "company": {"Entity"},
    "corporate-entity": {"Entity"},
    "legal-person": {"Entity"},
}


@dataclass
class Subject:
    """An entity to screen against the list."""
    name: str
    subject_type: str = "individual"     # individual | officer | psc | company | entity
    ref: str | None = None               # CH officer/psc id, or company number
    dob_year: int | None = None
    dob_month: int | None = None
    nationalities: list[str] = field(default_factory=list)
    identifiers: list[str] = field(default_factory=list)  # company number, passport, …
    country: str | None = None


@dataclass
class Match:
    subject_ref: str | None
    subject_type: str
    subject_name: str
    list: str                 # "UK_SANCTIONS"
    designation_id: str
    matched_name: str
    group_type: str
    regime_name: str
    score: float
    verdict: str              # RED | AMBER
    matched_fields: dict
    evidence: dict

    def to_dict(self) -> dict:
        return {
            "subject_ref": self.subject_ref,
            "subject_type": self.subject_type,
            "subject_name": self.subject_name,
            "list": self.list,
            "matched_designation_id": self.designation_id,
            "matched_name": self.matched_name,
            "group_type": self.group_type,
            "regime_name": self.regime_name,
            "score": round(self.score, 4),
            "verdict": self.verdict,
            "matched_fields": self.matched_fields,
            "evidence": self.evidence,
        }


_TOKEN_EQ = 0.92  # two name tokens "align" if Jaro-Winkler >= this (Muhammad~Mohammad)


def _name_score(a_norm: str, b_norm: str) -> tuple[float, float, float]:
    """Return (combined, jaro_winkler, token_set) in 0..1. Combined = max of the two.

    We deliberately avoid partial_ratio as the headline metric — it over-fires on
    substrings ("John" inside "Johnson"). Jaro-Winkler rewards shared prefixes;
    token-set handles reordered / extra / missing tokens.
    """
    if not a_norm or not b_norm:
        return (0.0, 0.0, 0.0)
    jw = float(_jw(a_norm, b_norm))
    ts = fuzz.token_set_ratio(a_norm, b_norm) / 100.0
    return (max(jw, ts), jw, ts)


def _token_alignment(subj_tokens: list[str], name_tokens: list[str],
                     token_df: dict[str, int]) -> tuple[int, bool, float]:
    """How well two token lists line up, used to defuse the token-set subset trap.

    `token_set_ratio` returns 1.0 whenever one name's tokens are a subset of the
    other's — so a mononym designation ("HASSAN") scores a perfect match against
    anyone called "... Hassan ...". We count how many tokens genuinely align
    (fuzzily), whether any aligned token is *distinctive* (rare across the list),
    and the coverage of the shorter name. The screener then refuses to raise an
    alert on a lone common token.

    Returns (aligned_count, has_distinctive_alignment, short_coverage).
    """
    if not subj_tokens or not name_tokens:
        return (0, False, 0.0)
    short, long_ = (subj_tokens, name_tokens) if len(subj_tokens) <= len(name_tokens) else (name_tokens, subj_tokens)
    used: set[int] = set()
    aligned = 0
    distinctive = False
    for t in short:
        for j, u in enumerate(long_):
            if j in used:
                continue
            if t == u or _jw(t, u) >= _TOKEN_EQ:
                used.add(j)
                aligned += 1
                if token_df.get(t, 0) <= COMMON_TOKEN_DF:
                    distinctive = True
                break
    return (aligned, distinctive, aligned / len(short))


class SanctionsIndex:
    """In-memory blocking index over UKSL designations.

    UKSL is small (~15k names) so we load name/phonetic keys into memory for fast,
    explainable candidate generation — no O(subjects x designations) full scan.
    """

    def __init__(self, designations: list[Designation]):
        self.designations = designations
        self._token_index: dict[str, set[int]] = defaultdict(set)
        self._phonetic_index: dict[str, set[int]] = defaultdict(set)
        self._identifier_index: dict[str, set[int]] = defaultdict(set)
        self._token_df: dict[str, int] = defaultdict(int)
        self._build()

    def _build(self) -> None:
        for idx, d in enumerate(self.designations):
            seen_tokens: set[str] = set()
            for name in d.names:
                toks = name.normalized_name.split(" ") if name.normalized_name else []
                for tok in toks:
                    if not tok:
                        continue
                    self._token_index[tok].add(idx)
                    if tok not in seen_tokens:
                        seen_tokens.add(tok)
                    code = _metaphone(tok)
                    if code:
                        self._phonetic_index[code].add(idx)
            for tok in seen_tokens:
                self._token_df[tok] += 1
            for ident in d.identifier_norms:
                if ident:
                    self._identifier_index[ident].add(idx)

    # -- candidate generation (blocking) --
    def _candidates(self, subj_tokens: list[str], subj_ids: set[str]) -> set[int]:
        cands: set[int] = set()
        for tok in subj_tokens:
            cands |= self._token_index.get(tok, set())
            code = _metaphone(tok)
            if code:
                cands |= self._phonetic_index.get(code, set())
        for ident in subj_ids:
            cands |= self._identifier_index.get(ident, set())
        return cands

    def _is_common(self, subj_tokens: list[str]) -> bool:
        """A subject whose every token is individually common (e.g. 'MOHAMMED
        AHMED') is a false-positive risk and must not reach RED without
        corroboration."""
        distinctive = [t for t in subj_tokens if self._token_df.get(t, 0) <= COMMON_TOKEN_DF]
        return len(distinctive) == 0

    def screen(self, subject: Subject, *, list_name: str = "UK_SANCTIONS") -> list[Match]:
        compatible = _COMPATIBLE.get(subject.subject_type.lower())
        is_entity = subject.subject_type.lower() in {"company", "entity", "corporate-entity", "legal-person"}
        # mirror the ingestion normalization policy exactly (symmetry): entities
        # drop corp suffixes but KEEP honorific/rank words, individuals the reverse
        subj_norm = N.normalize_name(
            subject.name, drop_corp_suffixes=is_entity, drop_honorifics=not is_entity)
        subj_tokens = subj_norm.split(" ") if subj_norm else []
        subj_ids: set[str] = set()
        for raw in subject.identifiers:
            n = N.normalize_identifier(raw)
            if n:
                subj_ids.add(n)
            subj_ids |= N.extract_identifier_tokens(raw)
        subj_nats = {N.normalize_name(x) for x in subject.nationalities if x}
        common = self._is_common(subj_tokens)

        best: dict[str, Match] = {}
        for idx in self._candidates(subj_tokens, subj_ids):
            d = self.designations[idx]
            if compatible and d.group_type not in compatible and not (subj_ids & d.identifier_norms):
                continue
            m = self._score_designation(subject, subj_norm, subj_ids, subj_nats, common, d, list_name)
            if m is None:
                continue
            prev = best.get(d.unique_id)
            if prev is None or m.score > prev.score:
                best[d.unique_id] = m
        return sorted(best.values(), key=lambda x: x.score, reverse=True)

    def _score_designation(self, subject, subj_norm, subj_ids, subj_nats, common,
                           d: Designation, list_name) -> Match | None:
        subj_tokens = subj_norm.split(" ") if subj_norm else []
        # best name score across primary + all aliases
        best_combined, best_jw, best_ts, matched_name = 0.0, 0.0, 0.0, ""
        aligned, distinctive, coverage = 0, False, 0.0
        for name in d.names:
            combined, jw, ts = _name_score(subj_norm, name.normalized_name)
            if combined > best_combined:
                best_combined, best_jw, best_ts, matched_name = combined, jw, ts, name.full_name
                name_tokens = name.normalized_name.split(" ") if name.normalized_name else []
                aligned, distinctive, coverage = _token_alignment(
                    subj_tokens, name_tokens, self._token_df)

        # identifier corroboration (exact passport / national-id / business reg)
        id_overlap = subj_ids & d.identifier_norms
        identifier = "exact" if id_overlap else None

        # Token-alignment gate: refuse a name-based alert that rests on a single
        # COMMON token (the token-set subset trap). An exact identifier always
        # passes. Otherwise we need >=2 aligned tokens, or one *distinctive*
        # aligned token that covers the shorter name.
        gate = (
            identifier == "exact"
            or aligned >= 2
            or (aligned >= 1 and distinctive and coverage >= 0.999)
        )
        if not gate:
            return None

        # dob corroboration / disconfirmation
        dob = None
        if subject.dob_year and d.dob_years:
            dob = "match" if subject.dob_year in d.dob_years else "mismatch"

        # nationality corroboration
        nationality = "match" if (subj_nats & d.nationalities_norm) else None

        has_corroboration = identifier == "exact" or dob == "match" or nationality == "match"
        has_disconfirm = dob == "mismatch"

        verdict = _verdict(best_combined, has_corroboration, has_disconfirm,
                           identifier == "exact", common)
        if verdict is None:
            return None

        matched_fields = {
            "name_score": round(best_combined, 4),
            "jaro_winkler": round(best_jw, 4),
            "token_set": round(best_ts, 4),
            "tokens_aligned": aligned,
            "name_coverage": round(coverage, 3),
            "dob": dob,
            "nationality": nationality,
            "identifier": identifier,
            "common_name": common,
            "matched_identifiers": sorted(id_overlap) or None,
        }
        evidence = {
            "unique_id": d.unique_id,
            "ofsi_group_id": d.ofsi_group_id,
            "group_type": d.group_type,
            "regime_name": d.regime_name,
            "designation_source": d.designation_source,
            "sanctions_imposed": d.sanctions_imposed,
            "date_designated": d.date_designated,
            "uk_statement_of_reasons": d.uk_statement_of_reasons,
            "aliases": [n.full_name for n in d.names if not n.is_primary][:8],
            "nationalities": d.nationalities,
            "other_information": (d.other_information or "")[:400] or None,
        }
        return Match(
            subject_ref=subject.ref,
            subject_type=subject.subject_type,
            subject_name=subject.name,
            list=list_name,
            designation_id=d.unique_id,
            matched_name=matched_name,
            group_type=d.group_type,
            regime_name=d.regime_name,
            score=best_combined if identifier != "exact" else max(best_combined, 0.99),
            verdict=verdict,
            matched_fields=matched_fields,
            evidence=evidence,
        )


def _verdict(name_score: float, has_corroboration: bool, has_disconfirm: bool,
             exact_identifier: bool, common: bool) -> str | None:
    """Map scores + corroboration to RED / AMBER / no-alert. See brief §8.

    Precedence:
      * an exact identifier (passport / national-id / business reg) is decisive -> RED
      * a strong name (>=0.93) corroborated by DOB / nationality, with no
        conflicting DOB, that is NOT a very common name -> RED
      * any name >= 0.85 (incl. a strong-but-uncorroborated or common name) -> AMBER
      * otherwise no alert

    False-positive guard: a common name (every token frequent across the list) can
    only reach RED via an exact identifier — never on name + DOB/nationality alone,
    because those corroborations are themselves common. A human confirms the AMBER.
    """
    if exact_identifier:
        return "RED"
    if (name_score >= RED_NAME_THRESHOLD and has_corroboration
            and not has_disconfirm and not common):
        return "RED"
    if name_score >= AMBER_NAME_THRESHOLD:
        return "AMBER"
    return None


def build_index(designations: list[Designation]) -> SanctionsIndex:
    return SanctionsIndex(designations)
