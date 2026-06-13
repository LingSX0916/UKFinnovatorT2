# Triage — web frontend

The FCA Financial-Promotions Triage console. A React app (loaded from CDN +
Babel standalone — no build step) recreated from the Claude Design mockup and
wired to the project's Python backend.

## What it does

- **Triage board** (`QueueView`) — a Kanban board (Inbox → Analysing →
  Red / Amber / Green). On load a background "agent" reads each queued complaint,
  calls the backend, and moves the card into a risk column. One complaint also
  arrives live mid-stream to show the flow.
- **Case detail** (`CaseView`) — two switchable layouts (Dossier / Signal):
  RAG verdict, rule breaches with the exact offending words highlighted in the
  advert, plus Warning List / Companies House / FS Register checks.
- **Intake** (`IntakeView`) — log a new complaint; the agent triages it.

## How it connects to the AI

`data.jsx → analyseAdvert()` POSTs to **`/scan`** (served by the Flask backend
in `backend/api.py`). The backend calls **OpenAI gpt-4o** grounded in the
repo-root **`FCA.md`** rules engine (v2.0 — 17 rules R1–R17) and authoritatively
cross-references the FCA Warning List (`data/warning_list.json`) against the
advert + promoter. The backend returns the rules-engine contract
(`overall_verdict` / `summary` / `rules[]` with `triggered`+`severity` …);
`mapBackendToAnalysis()` adapts it to the UI's triage shape (and stays tolerant
of the earlier PASS/FAIL/FLAG schema). If the call fails, a built-in keyword
heuristic (`fallbackAnalysis`) keeps the UI working offline.

## Run

From the repo root:

```bash
pip install -r backend/requirements.txt
cp .env.example .env          # then add your OPENAI_API_KEY
python main.py
```

Open <http://localhost:5050>. Flask serves this `web/` folder and the API from
the same origin, so there is no CORS setup and nothing else to start.

> Port 5050 by default — on macOS, port 5000 is taken by AirPlay / Control
> Center. Override with `PORT=8000 python main.py`.

> Note: the board auto-triages ~4 complaints on load, i.e. ~4 OpenAI calls each
> time the page is opened. Without a valid key it silently falls back to the
> local heuristic.

## Files

| File | Role |
|------|------|
| `Triage.html`   | Entry point — loads React, Babel, then the scripts below |
| `data.jsx`      | Backend call + response mapper, demo complaints, fallback |
| `components.jsx`| Presentational pieces (icons, RAG lights, breach cards, …) |
| `views.jsx`     | Board, case detail (2 layouts), intake form |
| `app.jsx`       | Orchestrator + the background triage agent loop |
| `styles.css`    | FCA visual language (maroon brand + GOV.UK RAG palette) |
