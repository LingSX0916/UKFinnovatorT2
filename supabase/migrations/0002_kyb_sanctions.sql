-- KYB & UK Sanctions Intelligence — schema.
--
-- The Flask backend writes these with the service_role key (which bypasses RLS),
-- exactly like the existing complaints table. RLS is enabled on every table; the
-- policies below describe the intended model for authenticated compliance users
-- if/when the client reads Supabase directly. audit_log gets INSERT + SELECT only
-- (no UPDATE/DELETE policy), so the trail is tamper-evident.
--
-- Apply: Supabase SQL Editor (paste + Run) or `supabase db push`.

create extension if not exists pg_trgm;

-- ───────────────────────── Sanctions (UKSL) ─────────────────────────
create table if not exists public.sanctions_designation (
  unique_id               text primary key,        -- UKSL Unique ID
  ofsi_group_id           text,                     -- legacy OFSI Group ID (nullable)
  un_reference_number     text,
  group_type              text not null,            -- Individual | Entity | Ship
  regime_name             text not null,
  designation_source      text,                     -- UK | UN | UK & UN
  sanctions_imposed       text[],                   -- Asset freeze, Travel ban, …
  uk_statement_of_reasons text,
  other_information        text,
  date_designated         date,
  last_updated            date,
  raw                     jsonb not null,           -- full source record, lossless
  created_at              timestamptz default now()
);

create table if not exists public.sanctions_name (
  id              bigserial primary key,
  designation_id  text references public.sanctions_designation(unique_id) on delete cascade,
  name_type       text,            -- Primary Name | Primary Name Variation | Alias
  alias_strength  text,            -- good quality | low quality | null
  full_name       text,
  normalized_name text not null    -- uppercased, de-punctuated, transliterated
);
create index if not exists sanctions_name_trgm on public.sanctions_name using gin (normalized_name gin_trgm_ops);
create index if not exists sanctions_name_designation on public.sanctions_name (designation_id);

create table if not exists public.sanctions_identifier (
  id               bigserial primary key,
  designation_id   text references public.sanctions_designation(unique_id) on delete cascade,
  id_type          text,           -- passport | national_id | business_registration | imo
  id_value         text,
  normalized_value text,           -- digits/letters only, for exact matching
  additional_info  text
);
create index if not exists sanctions_identifier_value on public.sanctions_identifier (normalized_value);

create table if not exists public.sanctions_dob (
  id             bigserial primary key,
  designation_id text references public.sanctions_designation(unique_id) on delete cascade,
  dob_raw        text,             -- may be partial e.g. 'dd/mm/1970'
  dob_year       int,
  dob_month      int,
  dob_day        int
);

create table if not exists public.sanctions_address (
  id             bigserial primary key,
  designation_id text references public.sanctions_designation(unique_id) on delete cascade,
  line1 text, line2 text, line3 text, line4 text, line5 text, line6 text,
  postal_code text, country text
);

create table if not exists public.sanctions_attribute (   -- nationality, position, …
  id             bigserial primary key,
  designation_id text references public.sanctions_designation(unique_id) on delete cascade,
  attr_key       text not null,
  attr_value     text
);

create table if not exists public.sanctions_import (      -- provenance per ingest run
  id                bigserial primary key,
  source_file       text not null,
  file_sha256       text not null,
  designation_count int not null,
  parsed_at         timestamptz default now(),
  notes             text
);

-- ──────────────────── FCA Warning List (from data/) ────────────────────
create table if not exists public.warning_list_entry (
  id              bigserial primary key,
  entry_type      text,            -- firm | individual | domain
  name            text,
  normalized_name text not null,
  domain          text,
  details         jsonb,
  source          text default 'fca_warning_list'
);
create index if not exists warning_list_trgm on public.warning_list_entry using gin (normalized_name gin_trgm_ops);

-- ─────────────────────── Companies House cache ───────────────────────
create table if not exists public.company (
  company_number text primary key,
  name text, normalized_name text,
  status text, company_type text, jurisdiction text,
  date_of_creation date,
  sic_codes text[],
  registered_office jsonb,
  accounts jsonb,
  confirmation_statement jsonb,
  raw jsonb not null,
  fetched_at timestamptz default now()
);

create table if not exists public.officer (
  id text primary key,
  company_number text references public.company(company_number) on delete cascade,
  name text, normalized_name text,
  officer_role text,
  appointed_on date, resigned_on date,
  nationality text, country_of_residence text,
  dob_month int, dob_year int,
  raw jsonb not null
);

create table if not exists public.psc (
  id text primary key,
  company_number text references public.company(company_number) on delete cascade,
  kind text,
  name text, normalized_name text,
  natures_of_control text[],
  notified_on date, ceased_on date,
  identification jsonb,
  raw jsonb not null
);

create table if not exists public.ownership_edge (
  id bigserial primary key,
  company_number text references public.company(company_number) on delete cascade,
  owner_kind text,
  owner_ref text,
  owner_name text,
  ownership_band text,
  nature_of_control text[],
  is_direct boolean default true,
  depth int default 1
);

-- ─────────────────────── Screening & risk ───────────────────────
create table if not exists public.screening_run (
  id uuid primary key default gen_random_uuid(),
  company_number text,
  run_by text,
  run_at timestamptz default now(),
  lists_checked text[],
  overall_verdict text,            -- RED | AMBER | GREEN
  subjects_screened int,
  summary text
);

create table if not exists public.screening_match (
  id uuid primary key default gen_random_uuid(),
  run_id uuid references public.screening_run(id) on delete cascade,
  subject_type text,               -- officer | psc | company
  subject_ref text,
  subject_name text,
  list text,                       -- UK_SANCTIONS | FCA_WARNING
  matched_designation_id text,
  matched_name text,
  score numeric,
  verdict text,                    -- RED | AMBER
  matched_fields jsonb,
  evidence jsonb,
  decision text default 'pending', -- pending | confirmed | dismissed
  reviewer text, decided_at timestamptz, reviewer_note text
);
create index if not exists screening_match_run on public.screening_match (run_id);

create table if not exists public.risk_assessment (
  id uuid primary key default gen_random_uuid(),
  company_number text,
  run_id uuid references public.screening_run(id) on delete cascade,
  overall_rating text,             -- GREEN | AMBER | RED
  score numeric,
  factors jsonb not null,          -- [{code,label,triggered,severity,weight,evidence,provision,confidence}]
  created_at timestamptz default now()
);

create table if not exists public.audit_log (           -- append-only; tamper-evident
  id bigserial primary key,
  actor text, action text, entity text, entity_ref text,
  payload jsonb, created_at timestamptz default now()
);

-- ───────────────────────────── RLS ─────────────────────────────
-- service_role (backend) bypasses RLS. Policies below are for the `authenticated`
-- role in case the client ever reads Supabase directly.
alter table public.sanctions_designation enable row level security;
alter table public.sanctions_name        enable row level security;
alter table public.sanctions_identifier  enable row level security;
alter table public.sanctions_dob         enable row level security;
alter table public.sanctions_address     enable row level security;
alter table public.sanctions_attribute   enable row level security;
alter table public.sanctions_import      enable row level security;
alter table public.warning_list_entry    enable row level security;
alter table public.company               enable row level security;
alter table public.officer               enable row level security;
alter table public.psc                   enable row level security;
alter table public.ownership_edge        enable row level security;
alter table public.screening_run         enable row level security;
alter table public.screening_match       enable row level security;
alter table public.risk_assessment       enable row level security;
alter table public.audit_log             enable row level security;

-- Reference data: authenticated users may READ.
do $$
declare t text;
begin
  foreach t in array array['sanctions_designation','sanctions_name','sanctions_identifier',
      'sanctions_dob','sanctions_address','sanctions_attribute','sanctions_import',
      'warning_list_entry','company','officer','psc','ownership_edge'] loop
    execute format('drop policy if exists %I_read on public.%I;', t, t);
    execute format('create policy %I_read on public.%I for select to authenticated using (true);', t, t);
  end loop;
  -- Screening / matches / risk: authenticated users may read and write.
  foreach t in array array['screening_run','screening_match','risk_assessment'] loop
    execute format('drop policy if exists %I_rw on public.%I;', t, t);
    execute format('create policy %I_rw on public.%I for all to authenticated using (true) with check (true);', t, t);
  end loop;
end $$;

-- audit_log: INSERT + SELECT only (NO update/delete policy) for authenticated.
drop policy if exists audit_log_insert on public.audit_log;
drop policy if exists audit_log_select on public.audit_log;
create policy audit_log_insert on public.audit_log for insert to authenticated with check (true);
create policy audit_log_select on public.audit_log for select to authenticated using (true);

-- Append-only enforcement that ALSO binds the table owner and the service_role
-- key (RLS does not constrain service_role, so the no-UPDATE/DELETE-policy alone
-- is not tamper-evident). This trigger makes the audit trail genuinely immutable.
create or replace function public.audit_log_no_mutate()
returns trigger language plpgsql as $$
begin
  raise exception 'audit_log is append-only; % is not permitted', tg_op;
end $$;

drop trigger if exists audit_log_immutable on public.audit_log;
create trigger audit_log_immutable
  before update or delete on public.audit_log
  for each row execute function public.audit_log_no_mutate();
