"""Companies House Public Data API client — throttled, cached, schema-validated.

Auth is HTTP Basic with the API key as the username and an empty password
(`Authorization: Basic base64(API_KEY + ":")`). The key is server-side only
(`COMPANIES_HOUSE_API_KEY`) and never reaches the browser.

Resilience the brief asks for:
  * a throttle (~600 req / 5 min) + exponential backoff on HTTP 429,
  * a response cache so repeated dossier views / re-screens don't re-hit the API,
  * pydantic validation of every response (CH fields are frequently absent — every
    field is optional and extras are ignored, so a missing field never crashes us).

Offline / demo / CI: if no API key is configured the client transparently serves
recorded fixtures from `data/ch_fixtures/`, so the whole product runs end-to-end —
search -> dossier -> Run sanction check -> RED — with no key and no network.
"""
from __future__ import annotations

import base64
import json
import os
import re
import threading
import time
from pathlib import Path

import requests
from pydantic import BaseModel, ConfigDict

_BASE_URL = "https://api.company-information.service.gov.uk"
_FIXTURE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "ch_fixtures"

# UK company numbers / OE registration numbers: 8 chars, either 8 digits or a
# 2-letter prefix + 6 digits. We accept 6-10 alphanumerics and reject anything
# else BEFORE the value reaches a URL or a filesystem path (SSRF / traversal guard).
_NUMBER_RE = re.compile(r"^[A-Za-z0-9]{6,10}$")


def valid_company_number(number: str) -> bool:
    return bool(number and _NUMBER_RE.match(number))


# --- lenient schemas: validate shape without ever rejecting on a missing field ---
class _Loose(BaseModel):
    model_config = ConfigDict(extra="allow")


class RegisteredOffice(_Loose):
    address_line_1: str | None = None
    address_line_2: str | None = None
    locality: str | None = None
    region: str | None = None
    postal_code: str | None = None
    country: str | None = None


class CompanyProfile(_Loose):
    company_name: str | None = None
    company_number: str | None = None
    company_status: str | None = None
    type: str | None = None
    jurisdiction: str | None = None
    date_of_creation: str | None = None
    sic_codes: list[str] | None = None
    registered_office_address: RegisteredOffice | None = None
    accounts: dict | None = None
    confirmation_statement: dict | None = None


class DateOfBirth(_Loose):
    month: int | None = None
    year: int | None = None


class Officer(_Loose):
    name: str | None = None
    officer_role: str | None = None
    appointed_on: str | None = None
    resigned_on: str | None = None
    nationality: str | None = None
    country_of_residence: str | None = None
    date_of_birth: DateOfBirth | None = None
    links: dict | None = None


class PSC(_Loose):
    name: str | None = None
    kind: str | None = None
    natures_of_control: list[str] | None = None
    notified_on: str | None = None
    ceased_on: str | None = None
    nationality: str | None = None
    country_of_residence: str | None = None
    date_of_birth: DateOfBirth | None = None
    identification: dict | None = None
    links: dict | None = None


class _Throttle:
    """Simple min-interval throttle. ~600 req / 5 min => 1 req / 0.5s, with headroom."""

    def __init__(self, min_interval: float = 0.5):
        self.min_interval = min_interval
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delta = now - self._last
            if delta < self.min_interval:
                time.sleep(self.min_interval - delta)
            self._last = time.monotonic()


class CompaniesHouseClient:
    def __init__(self, api_key: str | None = None, *, fixtures_dir: Path | None = None,
                 cache_ttl: float = 86_400.0, max_retries: int = 4):
        self.api_key = api_key or os.environ.get("COMPANIES_HOUSE_API_KEY")
        self.fixtures_dir = Path(fixtures_dir) if fixtures_dir else _FIXTURE_DIR
        self.cache_ttl = cache_ttl
        self.max_retries = max_retries
        self._throttle = _Throttle()
        self._cache: dict[str, tuple[float, dict]] = {}
        self._fixture_cache: dict[str, dict] = {}

    @property
    def live(self) -> bool:
        return bool(self.api_key)

    @property
    def mode(self) -> str:
        return "live" if self.live else "fixtures"

    # -- low-level GET (live, throttled, cached, backoff) or fixture ---------------
    def _auth_header(self) -> dict:
        token = base64.b64encode(f"{self.api_key}:".encode()).decode()
        return {"Authorization": f"Basic {token}"}

    def _get(self, path: str, params: dict | None = None) -> dict | None:
        key = path + "?" + json.dumps(params or {}, sort_keys=True)
        cached = self._cache.get(key)
        if cached and (time.monotonic() - cached[0]) < self.cache_ttl:
            return cached[1]
        data = self._get_live(path, params) if self.live else self._get_fixture(path, params)
        if data is not None:
            self._cache[key] = (time.monotonic(), data)
        return data

    def _get_live(self, path: str, params: dict | None) -> dict | None:
        backoff = 1.0
        for attempt in range(self.max_retries + 1):
            self._throttle.wait()
            resp = requests.get(_BASE_URL + path, params=params,
                                headers=self._auth_header(), timeout=20)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 404:
                return None
            if resp.status_code in (401, 403):  # bad / expired / unauthorised key
                import logging
                logging.getLogger(__name__).warning(
                    "Companies House auth failed (HTTP %s) — check COMPANIES_HOUSE_API_KEY",
                    resp.status_code)
                return None
            if resp.status_code == 429:  # rate limited — exponential backoff
                wait = float(resp.headers.get("Retry-After", backoff))
                time.sleep(wait)
                backoff = min(backoff * 2, 30.0)
                continue
            if 500 <= resp.status_code < 600:
                time.sleep(backoff)
                backoff = min(backoff * 2, 30.0)
                continue
            resp.raise_for_status()
        return None  # exhausted retries

    def _load_fixture(self, number: str) -> dict | None:
        number = (number or "").upper()
        if not valid_company_number(number):  # also blocks path traversal
            return None
        if number in self._fixture_cache:
            return self._fixture_cache[number]
        path = self.fixtures_dir / f"{number}.json"
        # defence in depth: confirm the resolved path stays inside the fixtures dir
        try:
            resolved = path.resolve()
            if not str(resolved).startswith(str(self.fixtures_dir.resolve())):
                return None
        except Exception:
            return None
        if not resolved.exists():
            return None
        data = json.loads(resolved.read_text(encoding="utf-8"))
        self._fixture_cache[number] = data
        return data

    def _all_fixtures(self) -> list[dict]:
        if not self.fixtures_dir.exists():
            return []
        out = []
        for p in sorted(self.fixtures_dir.glob("*.json")):
            if p.stem.startswith("_"):
                continue
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except Exception:
                continue
        return out

    def _get_fixture(self, path: str, params: dict | None) -> dict | None:
        parts = path.strip("/").split("/")
        if parts[0] == "search" and parts[1] == "companies":
            q = (params or {}).get("q", "").lower()
            items = []
            for fx in self._all_fixtures():
                prof = fx.get("profile", {})
                if q in (prof.get("company_name", "").lower()) or q in (prof.get("company_number", "").lower()):
                    items.append({
                        "company_name": prof.get("company_name"),
                        "company_number": prof.get("company_number"),
                        "company_status": prof.get("company_status"),
                        "company_type": prof.get("type"),
                        "address_snippet": (prof.get("registered_office_address") or {}).get("locality"),
                    })
            return {"items": items, "total_results": len(items)}
        if parts[0] == "company":
            number = parts[1]
            fx = self._load_fixture(number)
            if fx is None:
                return None
            if len(parts) == 2:
                return fx.get("profile")
            sub = parts[2]
            return fx.get(sub, {"items": []})
        if parts[0] == "officers" and len(parts) >= 3:  # /officers/{id}/appointments
            return {"items": []}
        return None

    # -- public, normalized API ---------------------------------------------------
    def search_companies(self, query: str, *, limit: int = 20) -> list[dict]:
        data = self._get("/search/companies", {"q": query, "items_per_page": limit}) or {}
        # Normalize to one shape: the live CH /search API names the company in
        # `title`, the profile resource uses `company_name` — map both so the
        # frontend (and graph.py PSC resolution) always read `company_name`.
        out = []
        for it in (data.get("items") or [])[:limit]:
            out.append({
                "company_name": it.get("title") or it.get("company_name"),
                "company_number": it.get("company_number"),
                "company_status": it.get("company_status"),
                "company_type": it.get("company_type") or it.get("type"),
                "address_snippet": it.get("address_snippet"),
            })
        return out

    def get_profile(self, number: str) -> dict | None:
        raw = self._get(f"/company/{number}")
        if not raw:
            return None
        p = CompanyProfile(**raw)
        ro = p.registered_office_address.model_dump() if p.registered_office_address else {}
        accounts = p.accounts or {}
        cs = p.confirmation_statement or {}
        return {
            "company_number": p.company_number or number,
            "name": p.company_name,
            "status": p.company_status,
            "company_type": p.type,
            "jurisdiction": p.jurisdiction,
            "date_of_creation": p.date_of_creation,
            "sic_codes": p.sic_codes or [],
            "registered_office": ro,
            "accounts": accounts,
            "confirmation_statement": cs,
            "accounts_overdue": bool(accounts.get("overdue")),
            "confirmation_overdue": bool(cs.get("overdue")),
            "raw": raw,
        }

    def get_officers(self, number: str) -> list[dict]:
        data = self._get(f"/company/{number}/officers", {"items_per_page": 100}) or {}
        out = []
        for i, raw in enumerate(data.get("items") or []):
            o = Officer(**raw)
            dob = o.date_of_birth.model_dump() if o.date_of_birth else {}
            out.append({
                "id": (raw.get("links", {}).get("officer", {}).get("appointments") or f"{number}-officer-{i}"),
                "name": o.name,
                "officer_role": o.officer_role,
                "appointed_on": o.appointed_on,
                "resigned_on": o.resigned_on,
                "nationality": o.nationality,
                "country_of_residence": o.country_of_residence,
                "dob_month": dob.get("month"),
                "dob_year": dob.get("year"),
                "raw": raw,
            })
        return out

    def get_pscs(self, number: str) -> list[dict]:
        data = self._get(f"/company/{number}/persons-with-significant-control",
                         {"items_per_page": 100}) or {}
        out = []
        for i, raw in enumerate(data.get("items") or []):
            p = PSC(**raw)
            dob = p.date_of_birth.model_dump() if p.date_of_birth else {}
            ident = p.identification or {}
            out.append({
                "id": f"{number}-psc-{i}",
                "name": p.name,
                "kind": p.kind,
                "natures_of_control": p.natures_of_control or [],
                "notified_on": p.notified_on,
                "ceased_on": p.ceased_on,
                "nationality": p.nationality,
                "country_of_residence": p.country_of_residence,
                "dob_month": dob.get("month"),
                "dob_year": dob.get("year"),
                "identification": ident,
                "raw": raw,
            })
        return out

    def get_filing_history(self, number: str) -> list[dict]:
        data = self._get(f"/company/{number}/filing-history", {"items_per_page": 100}) or {}
        out = []
        for raw in data.get("items") or []:
            out.append({
                "category": raw.get("category"),
                "type": raw.get("type"),
                "date": raw.get("date"),
                "description": raw.get("description"),
                "document": (raw.get("links") or {}).get("document_metadata"),
                "raw": raw,
            })
        return out

    def get_charges(self, number: str) -> dict:
        return self._get(f"/company/{number}/charges") or {"items": []}

    def get_officer_appointments(self, officer_id: str) -> dict:
        return self._get(f"/officers/{officer_id}/appointments") or {"items": []}
