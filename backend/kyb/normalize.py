"""Shared, deterministic text normalization for sanctions matching.

This module is imported by BOTH the UKSL ingestion pipeline (`uksl.py`) and the
live screening matcher (`matching.py`). That is deliberate and load-bearing: the
normalized string a designation is *stored* under must be byte-for-byte the
string the matcher *computes* for an incoming officer/PSC/company. Any asymmetry
between the two sides silently turns a true sanctions hit into a miss — the worst
failure mode for a financial-crime tool. So there is exactly one implementation
of each transform and both sides call it.

Everything here is a pure function: same input -> same output, no I/O, no state.
"""
from __future__ import annotations

import re
import unicodedata

# Transliteration: map non-Latin scripts (Arabic, Cyrillic, Han, ...) to Latin so
# a Cyrillic source name and a Latin subject name can be compared. text-unidecode
# is the permissively-licensed twin of unidecode; we accept either and degrade to
# a no-op so the module never hard-fails on a missing optional dependency.
try:  # pragma: no cover - import wiring
    from unidecode import unidecode as _translit
except Exception:  # pragma: no cover
    try:
        from text_unidecode import unidecode as _translit
    except Exception:
        def _translit(s: str) -> str:  # type: ignore
            return s


# Honorifics / titles carry no identifying value and actively hurt token matching
# (UKSL stores them in a separate <Titles> element, but they also leak into names).
# Dropping them means "Mullah Mohammad Hassan" blocks against "Mohammad Hassan".
HONORIFICS = {
    "MR", "MRS", "MS", "MISS", "MX", "DR", "PROF", "PROFESSOR", "SIR", "DAME",
    "LORD", "LADY", "HON", "RT", "MULLAH", "MAULAVI", "MAWLAWI", "MOLAVI", "MOLAWI",
    "HAJI", "HAJJI", "AL-HAJJ", "ALHAJ", "SHEIKH", "SHAYKH", "SHEIK", "SHAIKH",
    "QARI", "HAFIZ", "MAULANA", "MOLLAH", "ENG", "ENGINEER", "GENERAL", "GEN",
    "COLONEL", "COL", "MAJOR", "CAPTAIN", "CAPT", "BRIGADIER", "COMMANDER", "LT",
    "LIEUTENANT", "SERGEANT", "SGT", "ADMIRAL", "MARSHAL",
}

# Corporate suffixes / form words. Kept for display but dropped from the matching
# token set, so "ACME LIMITED", "ACME LTD" and "ACME" share blocking keys. We only
# drop these when matching *entities* (drop_corp_suffixes=True), never individuals.
CORP_SUFFIXES = {
    "LTD", "LIMITED", "LLC", "LLP", "PLC", "INC", "INCORPORATED", "CORP",
    "CORPORATION", "CO", "COMPANY", "GMBH", "MBH", "SA", "SARL", "SAS", "BV", "NV",
    "AG", "SPA", "SRL", "PTE", "PVT", "PRIVATE", "OOO", "OAO", "ZAO", "PJSC",
    "OJSC", "JSC", "AO", "FZE", "FZC", "FZCO", "DMCC", "LLP", "KFT", "AS", "OY",
    "AB", "DOO", "EOOD", "OOD", "SP", "ZOO", "TOO", "TBK", "BHD", "SDN", "PT",
}

_PUNCT_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)
_WS_RE = re.compile(r"\s+")
_DATE_SEP_RE = re.compile(r"[\/\-.\s]+")


def transliterate(text: str) -> str:
    """NFKD-decompose, strip combining diacritics, then transliterate to ASCII.

    "Müller" -> "Muller"; "Алексей" -> "Aleksei"; "محمد" -> "mhmd".
    """
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    no_marks = "".join(c for c in decomposed if not unicodedata.combining(c))
    return _translit(no_marks)


def normalize_tokens(
    text: str,
    *,
    drop_corp_suffixes: bool = False,
    drop_honorifics: bool = True,
) -> list[str]:
    """Return the order-preserving list of normalized tokens for a name.

    Transliterate -> uppercase -> replace punctuation with spaces -> collapse
    whitespace -> drop honorifics (and optionally corporate suffixes). If the
    filters would empty the name (e.g. it was only a title), we fall back to the
    unfiltered tokens so a name never normalizes to nothing.
    """
    if not text:
        return []
    t = transliterate(text).upper()
    t = _PUNCT_RE.sub(" ", t)
    t = _WS_RE.sub(" ", t).strip()
    if not t:
        return []
    raw_tokens = t.split(" ")
    out: list[str] = []
    for tok in raw_tokens:
        if drop_honorifics and tok in HONORIFICS:
            continue
        if drop_corp_suffixes and tok in CORP_SUFFIXES:
            continue
        out.append(tok)
    return out or raw_tokens


def normalize_name(text: str, *, drop_corp_suffixes: bool = False,
                   drop_honorifics: bool = True) -> str:
    """Canonical normalized name: the joined, normalized token string.

    This is what gets stored in `sanctions_name.normalized_name` and what the
    matcher computes for each subject — the symmetry the module exists to keep.
    `drop_honorifics` is on for individuals (titles add no identifying value) but
    must be OFF for entities, where rank/role words ("General", "Marshal") are
    legitimate company-name tokens (General Dynamics, Marshal Trading) — dropping
    them would erase a distinctive token and weaken the alignment guard.
    """
    return " ".join(normalize_tokens(text, drop_corp_suffixes=drop_corp_suffixes,
                                     drop_honorifics=drop_honorifics))


def normalize_identifier(value: str) -> str:
    """Alphanumeric-only uppercase form for exact identifier matching.

    Used for passport / national-id / business-registration matching, where an
    exact hit is a strong corroborating signal. "07731902" -> "07731902";
    "GB 12 3456 78" -> "GB12345678".
    """
    if not value:
        return ""
    return re.sub(r"[^A-Z0-9]", "", transliterate(value).upper())


# Registration numbers in UKSL are stored as free text that can pack several
# numbers across countries into one element, e.g.
#   "(УНН/ИНН): 190950894 (Belarus),\n7704734000/770301001 (Russia)".
# For matching we want every distinct alphanumeric token that *could* be a reg
# number, so we extract candidate tokens rather than normalizing the whole blob.
_REG_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-]{3,}")


def extract_identifier_tokens(value: str, *, min_len: int = 5) -> set[str]:
    """Extract candidate identifier tokens from a free-text blob.

    A token qualifies if it is >= min_len alphanumerics AND contains at least one
    digit. The digit requirement drops pure-alpha noise (country names, "a.k.a")
    that otherwise leaks out of messy multi-number reg-number strings, while
    keeping real registration / passport / national-id numbers (which always
    carry digits).
    """
    if not value:
        return set()
    tokens = set()
    for raw in _REG_TOKEN_RE.findall(transliterate(value)):
        norm = re.sub(r"[^A-Z0-9]", "", raw.upper())
        if len(norm) >= min_len and any(c.isdigit() for c in norm):
            tokens.add(norm)
    return tokens


def parse_partial_dob(raw: str) -> tuple[int | None, int | None, int | None]:
    """Parse a UKSL DOB string into (year, month, day), None for unknown parts.

    UKSL writes partial dates with literal placeholders, e.g. 'dd/mm/1945' means
    "1945, day and month unknown". Full dates appear as '12/03/1980'. We extract a
    4-digit year wherever it sits and day/month only when present and in range.
    """
    if not raw:
        return (None, None, None)
    parts = _DATE_SEP_RE.split(raw.strip())
    year = month = day = None
    for p in parts:
        if re.fullmatch(r"\d{4}", p):
            year = int(p)
    if len(parts) == 3:
        d, m, y = parts
        if d.isdigit() and 1 <= int(d) <= 31:
            day = int(d)
        if m.isdigit() and 1 <= int(m) <= 12:
            month = int(m)
        if re.fullmatch(r"\d{4}", y):
            year = int(y)
    return (year, month, day)


def parse_uksl_date(raw: str) -> str | None:
    """Parse a UKSL 'dd/mm/yyyy' date into an ISO 'YYYY-MM-DD' string, else None.

    Returns None for partial/placeholder dates (so we never invent a precise date).
    """
    if not raw:
        return None
    m = re.fullmatch(r"\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*", raw)
    if not m:
        return None
    d, mo, y = (int(g) for g in m.groups())
    if not (1 <= mo <= 12 and 1 <= d <= 31):
        return None
    return f"{y:04d}-{mo:02d}-{d:02d}"
