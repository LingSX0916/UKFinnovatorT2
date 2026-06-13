# Deploying Triage (Render + Supabase)

The app is a Flask service that serves the React UI (`web/`) and the `/scan`
(OpenAI) and `/complaints` (Supabase) APIs from one origin.

## 0. Rotate the keys first ⚠️
The `service_role` key, the `sb_secret_…` key and the DB password were shared in
chat, so treat them as compromised. In the Supabase dashboard:
**Settings → API → roll the service-role/secret keys**, and **Database → reset
password**. Use the new service-role key everywhere below.

## 1. Create the database table
Run the migration on your project (`kbcstsfoipforuapqtev`), either way:

- **Dashboard:** SQL Editor → paste the contents of
  [`supabase/migrations/0001_complaints.sql`](supabase/migrations/0001_complaints.sql) → Run.
- **CLI:**
  ```bash
  supabase login
  supabase link --project-ref kbcstsfoipforuapqtev
  supabase db push
  ```

This creates a `complaints` table with RLS on and no policies — only the
backend's service-role key can read/write it (the browser never can).

## 2. Deploy to Render
1. Push this branch / merge it to `main` (the repo must be on GitHub).
2. Render → **New → Blueprint** → connect this repo. Render reads
   [`render.yaml`](render.yaml) and provisions a free Python web service.
3. Set the secret env vars in the Render dashboard (they are `sync: false`, so
   not stored in git):
   - `OPENAI_API_KEY` — your OpenAI key
   - `SUPABASE_URL` — `https://kbcstsfoipforuapqtev.supabase.co`
   - `SUPABASE_SERVICE_ROLE_KEY` — your **rotated** service-role key
   - (`OPENAI_MODEL` defaults to `gpt-4o`; `PYTHON_VERSION` is preset)
4. Deploy. Render runs `gunicorn backend.api:app` and gives you a public URL.

## 3. Verify
- `GET /health` → `{"status":"ok","persistence":true}` once Supabase env is set.
- Open the URL, log a complaint via the form, let it triage, then reload — it
  should reappear on the board (it was persisted to Supabase).

## Architecture note
Persistence is **backend-mediated**: the browser calls Flask `/complaints`, and
only Flask holds the service-role key. The anon/publishable key isn't needed in
this setup — nothing sensitive ever ships to the client. If you later want
realtime or direct client reads, add the anon key + RLS policies then.

## Local run (demo or with persistence)
```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env          # add OPENAI_API_KEY (+ SUPABASE_* for persistence)
python main.py                # http://localhost:5050
```
Without `SUPABASE_*` set, the app runs demo-only (no persistence) — the board
still works off its in-memory demo data.

## KYB & UK Sanctions module

The KYB engine ships in the same Flask service (routes under `/api/...`, console
at `/kyb`) and runs **offline by default** — recorded Companies House fixtures
plus a committed 30-designation sanctions sample — so it needs no extra secrets
to demo.

**Extra env vars (all optional, server-side only):**
- `COMPANIES_HOUSE_API_KEY` — live Companies House data (HTTP Basic, key as
  username). Without it the client serves `data/ch_fixtures/`.
- `UKSL_XML_PATH` — path to the full UK Sanctions List XML. Without it the engine
  falls back to `tests/kyb/fixtures/uksl_sample.xml`. Download the full file from
  the FCDO "UK Sanctions List" page on GOV.UK and drop it at `inputs/` (it is
  git-ignored — ~21 MB).

**Database (optional persistence):** apply the KYB schema the same way as the
complaints table — Dashboard SQL Editor → paste
[`supabase/migrations/0002_kyb_sanctions.sql`](supabase/migrations/0002_kyb_sanctions.sql)
→ Run, or `supabase db push`. RLS is on for every table; `audit_log` is
INSERT+SELECT only (tamper-evident).

**Ingest the sanctions list (reconciliation + optional Supabase upsert):**
```bash
python -m backend.kyb.ingest_uksl --file inputs/UK-Sanctions-List.xml            # reconcile + print
python -m backend.kyb.ingest_uksl --file inputs/UK-Sanctions-List.xml --supabase # also upsert (idempotent)
```

**Render:** add `COMPANIES_HOUSE_API_KEY` (sync:false) in the dashboard if you
want live data; `requirements.txt` already includes the new deps (`lxml`,
`rapidfuzz`, `jellyfish`, `unidecode`, `pydantic`, `reportlab`).
