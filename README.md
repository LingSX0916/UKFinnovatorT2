# UKFinnovatorT2 — FCA Promotions Triage Console

**Challenge:** Cambridge Spark — Financial Regulation in an AI-Driven World
**Theme:** Regulatory Compliance / RegTech
**Hackathon:** UKFin+ Innovator, 13–14 June 2026

---

## The idea

An AI tool that reads a financial advert — pasted text **or an uploaded screenshot** — and instantly tells you if it breaks FCA rules, which rule it breaks, and whether the company behind it is a known scam.

**Why it matters:** AI now lets anyone produce thousands of slick financial adverts in minutes — fake celebrity crypto ads, dodgy finfluencer "get rich quick" posts. Someone has to check every one of those against the FCA rulebook. Today that checking is done by hand, slowly. It cannot keep up with machines making ads at scale.

**What the tool does:** Submit an advert (text and/or an image) and in seconds it shows you:

- A red, amber, or green compliance verdict
- The exact rule it breaks, with the FCA provision cited (e.g. no risk warning → COBS 4.12A)
- The precise words in the ad that triggered the breach, quoted as evidence
- Whether the firm is on the FCA Warning List

**Who pays for it:** Not just the regulator — the firms. By law, any firm that signs off a financial advert must keep checking it stays compliant and re-confirm every 3 months. We automate that chore. Every regulated firm running ads is a potential customer.

---

## Architecture

| Layer | What it is |
|------|------------|
| **Frontend** | React 18 + Babel standalone — **no build step**, served as static files from `web/`. FCA visual language (maroon brand + GOV.UK RAG palette). |
| **Backend** | Flask (`backend/api.py`) serves the UI **and** the APIs from one origin (no CORS). `gunicorn` in production. |
| **Model** | OpenAI **gpt-4o** (text **and** vision) grounded in **`FCA.md`** — the v2.0 rules engine. `backend/scanner.py` prepends an explicit instruction and forces structured JSON output. |
| **Warning List** | `data/warning_list.json` cross-checked server-side against the advert + promoter; a hit forces RED. |
| **Persistence** *(optional)* | Supabase `complaints` table via `backend/store.py` (service-role key, server-side only). Off unless `SUPABASE_*` env is set — the app runs demo-only without it. |
| **Deploy** | Render blueprint (`render.yaml`). See **[DEPLOY.md](DEPLOY.md)**. |

The web app has three views: a **triage board** (a background agent reads each complaint and moves it across Inbox → Analysing → Red/Amber/Green), a **case detail** (two layouts, with the offending text highlighted in the advert / the uploaded image shown), and an **intake form** (paste text and/or upload a screenshot).

---

## Getting started (local)

```bash
git clone https://github.com/LingSX0916/UKFinnovatorT2.git
cd UKFinnovatorT2
python3.12 -m venv .venv && source .venv/bin/activate   # needs Python 3.10+
pip install -r backend/requirements.txt
cp .env.example .env          # add your OPENAI_API_KEY (gpt-4o, incl. vision)
python main.py                # → http://localhost:5050
```

Open <http://localhost:5050>. Notes:
- Port **5050** by default — on macOS, port 5000 is taken by AirPlay/Control Center (`PORT=8000 python main.py` to change).
- Without `OPENAI_API_KEY` the app still runs, but triage falls back to a keyword heuristic (image analysis needs the key).
- Persistence is off until you set `SUPABASE_*` and create the table — see **[DEPLOY.md](DEPLOY.md)**.

---

## The rules engine

The model is grounded in **[`FCA.md`](FCA.md)** — a v2.0 rules engine of **17 rules (R1–R17)** with minimal compliant/non-compliant pairs, a prescribed-text library, and a phrase bank. Each verdict must cite the provision and quote the exact offending phrase.

**Verdict logic:** a Warning List hit or any RED rule → **RED**; else any AMBER rule → **AMBER**; else **GREEN**.

The structured output per advert: `overall_verdict`, `summary`, `product_type`, `communicator_status`, and a `rules[]` array (each with `rule_id`, `triggered`, `severity`, `provision`, `evidence`, `explanation`, `suggested_fix`).

---

## Deployment

The repo is deploy-ready for **Render + Supabase**. Full runbook in **[DEPLOY.md](DEPLOY.md)**:
1. Create the Supabase `complaints` table (`supabase/migrations/0001_complaints.sql`).
2. Deploy on Render via `render.yaml` (Blueprint), setting `OPENAI_API_KEY` and the Supabase env vars in the dashboard.

> Secrets (OpenAI key, Supabase service-role key) live only in `.env` locally (gitignored) or the host's env vars — never in the repo.

---

## Demo adverts

Three fictional adverts engineered to exercise distinct rule paths:

**Green (clean PASS):** Authorised firm + FRN, balanced risk warning, no overstated returns, identified as a promotion.

**Amber (borderline):** Authorised firm, but past performance headlined ("18% last year"), FOMO language, no "past performance is not a guide to future returns".

**Red (showstopper):** Unauthorised promotion, false "FCA approved", guaranteed returns ("300%", "zero risk"), no prescribed crypto warning, and the named firm ("CoinVault Pro") matches the Warning List — forcing RED.

---

## Pitch deck outline (6 slides, 5 minutes)

1. **Hook** — 19,766 promotions amended or withdrawn by the FCA in 2024 (+97.5%). Most reviewed by hand.
2. **The gap** — No AI-specific rulebook; manual review cannot scale while generative AI mass-produces scams.
3. **Live demo** — Clean PASS → borderline AMBER → red showstopper with Warning List badge; text **and** screenshot input.
4. **Maps to the rule** — FG24/1, COBS 4.2.1R, COBS 4.12A, s21 FSMA, Warning List.
5. **Adoption path** — FCA AI Lab, Supercharged Sandbox; FCA reviewed ~480,000 sites in 2024.
6. **What's next** — Live Warning List API, vision on video reels, feedback loop into the FCA enforcement queue.

---

## Key FCA references

- [FG24/1 Financial promotions on social media](https://www.fca.org.uk/publications/finalised-guidance/fg24-1-finalised-guidance-financial-promotions-social-media)
- [FG23/3 Cryptoasset promotions guidance](https://www.fca.org.uk/publications/fg23-3-finalised-non-handbook-guidance-cryptoasset-financial-promotions)
- [COBS 4 — Communicating with clients](https://www.handbook.fca.org.uk/handbook/COBS/4/)
- [COBS 4.2.1R — Fair, clear and not misleading](https://www.handbook.fca.org.uk/handbook/COBS/4/2.html)
- [COBS 4.12A — Restricted Mass Market Investments / crypto](https://www.handbook.fca.org.uk/handbook/COBS/4/12A.html)
- [s21 FSMA 2000 — Financial promotion restriction](https://www.legislation.gov.uk/ukpga/2000/8/section/21)
- [FG22/5 Consumer Duty guidance](https://www.fca.org.uk/publication/finalised-guidance/fg22-5.pdf)

---

## Repo layout

```
FCA.md                     # the v2.0 rules engine (model system prompt)
main.py                    # local entrypoint (Flask dev server, :5050)
render.yaml                # Render deploy blueprint
DEPLOY.md                  # deploy + Supabase runbook
backend/
  api.py                   # Flask: serves web/ + /scan, /complaints, /health, /FCA.md; mounts kyb
  scanner.py               # OpenAI gpt-4o (text + vision) + the model instruction
  warning_list_checker.py  # FCA Warning List matching
  store.py                 # Supabase persistence (optional)
  kyb/                     # KYB & UK Sanctions Intelligence engines (see section below)
web/                       # React triage console (Triage.html + *.jsx) + KYB console (KYB.html + kyb-*.jsx)
data/                      # warning_list.json + demo adverts; ch_fixtures/ + warning_list_kyb.json
supabase/migrations/       # complaints table + 0002 kyb_sanctions schema
tests/kyb/                 # offline KYB engine + API tests
frontend/                  # legacy Streamlit UI (superseded by web/)
```

---

## KYB & UK Sanctions Intelligence (`backend/kyb` + `/kyb` console)

The "is the company behind the advert legit?" pillar, built as a company
due-diligence + sanctions-screening engine. Open the console at **`/kyb`**
(linked from the Triage board), search a UK company, and hit **Run sanction
check** to screen the company, every officer and every beneficial owner against
the **UK Sanctions List** and the **FCA Warning List**, then roll the results
into an **FCA / FATF risk rating** where every factor cites its regulation and
quotes its evidence.

**What it does**

- **UKSL ingestion** — parses the full UK Sanctions List XML (6,194 designations).
  The reconciliation test proves: count parity (parsed == file), **distinct-ID
  parity** (no duplicate/empty UniqueIDs), **zero unmapped element types** (every
  element is mapped, else CI fails loudly), and **child-record value parity**
  (parsed names/aliases/DOBs/identifiers == source counts) — so "nothing silently
  dropped" is demonstrable, not asserted. Native-script (Cyrillic/Arabic) names are
  transliterated and indexed as searchable aliases. See `backend/kyb/uksl.py` and
  `python -m backend.kyb.ingest_uksl --file inputs/UK-Sanctions-List.xml`.
- **Explainable matching** (`matching.py`) — Jaro-Winkler + token-set scoring with
  transliteration, DOB / nationality / registration-number corroboration, and
  false-positive guards (a common name never auto-reds; an exact reg number is
  decisive). Every match carries its sub-scores, the regime, the **UK Statement of
  Reasons** and a citation.
- **UBO graph** (`graph.py`) — resolves corporate PSCs to their own owners to find
  *indirect / ultimate* beneficial owners, with cycle detection and effective-%
  down each chain; nodes are coloured by screening result.
- **FCA / FATF risk engine** (`risk.py`) — SANCTIONS_MATCH, the OFSI **ownership &
  control (>50%)** rule, WARNING_LIST_MATCH, HIGH_RISK_JURISDICTION, beneficial-
  ownership opacity, complex structure and filing risk — deterministic precedence,
  every factor cited.
- **Companies House client** (`companies_house.py`) — throttled, backed-off,
  cached, pydantic-validated. Falls back to recorded fixtures so the whole flow
  runs **offline** (`/kyb` works with no API key and no sanctions file).
- **Audit & export** — confirm/dismiss each match with a note (immutable audit
  log); export the dossier as JSON or a PDF case file.

**Run it**

```bash
pip install -r backend/requirements.txt
python main.py            # http://localhost:5050  → open /kyb
```

Optional: set `COMPANIES_HOUSE_API_KEY` for live company data and `UKSL_XML_PATH`
to the full sanctions file (download from the FCDO "UK Sanctions List" page on
GOV.UK). Without them, the console runs on committed fixtures.

**Tests**: `pytest tests/kyb` (offline; engines, reconciliation, API).

**Integration with the promotions console**: a Warning-List or sanctions hit on
the firm behind an advert reinforces its RED verdict (consistent with `FCA.md`
§8). The dossier link and the `/api/company/{n}/screen` endpoint expose the
company RAG rating + sanctions/Warning-List flags back to the triage flow.

**Security & known limitations (next steps, honest about scope):**
- **Auth** — the KYB routes are unauthenticated like the rest of the demo app.
  Before production, gate the write routes (`/screen`, `/decision`), derive the
  audit `actor` from the authenticated principal (the API already prefers an
  `X-KYB-User` header), and lock CORS to the frontend origin. Company numbers are
  validated (`^[A-Z0-9]{6,10}$`) to block SSRF/path-traversal; `audit_log` has a
  DB trigger making it genuinely append-only.
- **Supabase RLS** policies are scaffolded for the `authenticated` role for when a
  client reads Supabase directly; today all access is backend-mediated via the
  service-role key. Tighten to owner/tenant scoping before enabling direct reads.
- **Matching** is triage, not enforcement: cross-script (e.g. Arabic vowel-less)
  transliteration can still weaken a name-only match, and the OFSI ownership rule
  aggregates effective % across chains using declared PSC bands (a conservative
  estimate). A human compliance officer confirms every match.
- Out of scope (clean seams left): live PEP/adverse-media feeds, non-UK
  registries, and a full re-screen that re-hydrates prior confirm/dismiss
  decisions from `screening_match`.
---

## Team

Victor · Pallavi · Raghav · Utkarsh · Jiad · Brandon

GitHub: [CRaghav21](https://github.com/CRaghav21) · [PallaviPatil-2458](https://github.com/PallaviPatil-2458) · Jiad (jiadcheema98)
