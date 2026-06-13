KYB & UK Sanctions Intelligence — company due diligence + sanctions screening.

The "is the company behind this advert legit?" pillar. Pure, deterministic,
unit-tested engines (no I/O inside scoring) wired to Companies House + Supabase by
the API/store layers. Mirrors FCA.md's house rule: no verdict without evidence.

Files:
  normalize.py        — shared text normalization (transliterate, de-punctuate,
                        identifier + partial-DOB parsing). Imported by BOTH the
                        ingester and the matcher so stored and queried forms match.
  uksl.py             — parse the UK Sanctions List XML to normalized designations.
                        KNOWN_PATHS + audit_paths() prove 100% field coverage.
  ingest_uksl.py      — CLI: reconcile (count parity + zero unmapped) and optionally
                        upsert to Supabase. `python -m backend.kyb.ingest_uksl --file ...`
  matching.py         — explainable fuzzy matcher (Jaro-Winkler + token-set), blocking,
                        corroboration, RED/AMBER thresholds, false-positive guards.
  warning_list.py     — FCA Warning List screening (firm / domain / individual),
                        reusing data/warning_list.json + data/warning_list_kyb.json.
  companies_house.py  — CH API client: throttle, 429 backoff, cache, pydantic
                        validation; offline fixture fallback (data/ch_fixtures/).
  graph.py            — UBO/ownership graph: resolve corporate PSCs recursively to
                        ultimate owners; cycle detection; effective ownership %.
  risk.py             — FCA/FATF risk engine: factors (each cited), OFSI ownership &
                        control (>50%), deterministic aggregation precedence.
  screening.py        — orchestrator behind "Run sanction check": screen company +
                        officers + UBOs, run risk, return one structured result.
  api.py              — Flask blueprint: /api/company/*, /api/screening/*.
  store.py            — optional Supabase persistence (service-role; demo-safe).
  export_pdf.py       — PDF case-file export (reportlab; JSON fallback).

Tests: tests/kyb/  (run offline: `pytest tests/kyb`).
