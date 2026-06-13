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
