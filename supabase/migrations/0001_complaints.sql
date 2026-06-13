-- Triage persistence: one row per triaged complaint.
-- The Flask backend reads/writes this with the service_role key, which bypasses
-- RLS. RLS is enabled with NO policies, so the anon/publishable key cannot touch
-- this table from the browser — all access goes through the backend.

create table if not exists public.complaints (
  ref        text primary key,           -- e.g. FP-2026-04921
  created_at timestamptz not null default now(),
  promoter   text,
  rag        text,                        -- red | amber | green
  payload    jsonb not null               -- the full UI complaint card incl. analysis
);

create index if not exists complaints_created_at_idx on public.complaints (created_at desc);

alter table public.complaints enable row level security;
-- (intentionally no policies: service_role only)
