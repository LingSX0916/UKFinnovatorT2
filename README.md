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
  api.py                   # Flask: serves web/ + /scan, /complaints, /health, /FCA.md
  scanner.py               # OpenAI gpt-4o (text + vision) + the model instruction
  warning_list_checker.py  # FCA Warning List matching
  store.py                 # Supabase persistence (optional)
web/                       # the React triage console (Triage.html + *.jsx + styles.css)
data/                      # warning_list.json + demo adverts
supabase/migrations/       # complaints table
frontend/                  # legacy Streamlit UI (superseded by web/)
```

---

## Team

Victor · Pallavi · Raghav · Utkarsh · Jiad · Brandon

GitHub: [CRaghav21](https://github.com/CRaghav21) · [PallaviPatil-2458](https://github.com/PallaviPatil-2458)
