-- Academic Context API — initial schema
-- See documentation/3-db_tables.md

-- Extensions
create extension if not exists vector with schema extensions;
create extension if not exists pgcrypto;

-- Helper: updated_at
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- 1. students
create table if not exists public.students (
  id uuid primary key default gen_random_uuid(),
  copilot_user_id text unique not null,
  name text,
  email text,
  timezone text not null default 'Asia/Manila',
  preferred_study_style text,
  preferred_study_times jsonb not null default '[]'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create trigger set_students_updated_at
before update on public.students
for each row execute function public.set_updated_at();

create index if not exists idx_students_copilot_user_id
on public.students (copilot_user_id);

-- 2. courses
create table if not exists public.courses (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students(id) on delete cascade,
  course_code text,
  course_name text not null,
  term text,
  instructor text,
  difficulty_level int not null default 3 check (difficulty_level between 1 and 5),
  color_label text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(student_id, course_code, term)
);

create trigger set_courses_updated_at
before update on public.courses
for each row execute function public.set_updated_at();

create index if not exists idx_courses_student_id on public.courses (student_id);
create index if not exists idx_courses_student_course_code on public.courses (student_id, course_code);

-- 3. documents
create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students(id) on delete cascade,
  course_id uuid references public.courses(id) on delete set null,
  storage_bucket text default 'academic-documents',
  storage_path text,
  file_name text,
  file_type text,
  source_text text,
  processing_status text not null default 'pending'
    check (processing_status in ('pending', 'processing', 'completed', 'failed')),
  extraction_status text not null default 'not_started'
    check (extraction_status in ('not_started', 'processing', 'completed', 'failed')),
  error_message text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create trigger set_documents_updated_at
before update on public.documents
for each row execute function public.set_updated_at();

create index if not exists idx_documents_student_id on public.documents (student_id);
create index if not exists idx_documents_course_id on public.documents (course_id);
create index if not exists idx_documents_processing_status on public.documents (processing_status);

-- 4. document_chunks
create table if not exists public.document_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  student_id uuid not null references public.students(id) on delete cascade,
  course_id uuid references public.courses(id) on delete set null,
  chunk_index int not null default 0,
  chunk_text text not null,
  token_count int,
  page_number int,
  metadata jsonb not null default '{}'::jsonb,
  embedding extensions.vector(1536),
  created_at timestamptz not null default now(),
  unique(document_id, chunk_index)
);

create index if not exists idx_document_chunks_document_id on public.document_chunks (document_id);
create index if not exists idx_document_chunks_student_id on public.document_chunks (student_id);
create index if not exists idx_document_chunks_course_id on public.document_chunks (course_id);

create index if not exists idx_document_chunks_embedding_hnsw
on public.document_chunks
using hnsw (embedding extensions.vector_cosine_ops);

-- 5. academic_items (no priority column — Copilot decides)
create table if not exists public.academic_items (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students(id) on delete cascade,
  course_id uuid references public.courses(id) on delete set null,
  document_id uuid references public.documents(id) on delete set null,
  type text not null check (
    type in ('assignment', 'exam', 'quiz', 'project', 'reading', 'presentation', 'lab', 'other')
  ),
  title text not null,
  description text,
  due_date timestamptz,
  due_date_confidence numeric not null default 0 check (due_date_confidence >= 0 and due_date_confidence <= 1),
  weight numeric check (weight is null or weight >= 0),
  estimated_hours numeric check (estimated_hours is null or estimated_hours >= 0),
  confidence_score numeric not null default 0 check (confidence_score >= 0 and confidence_score <= 1),
  status text not null default 'pending' check (
    status in ('pending', 'confirmed', 'in_progress', 'completed', 'cancelled')
  ),
  needs_confirmation boolean not null default false,
  source_quote text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create trigger set_academic_items_updated_at
before update on public.academic_items
for each row execute function public.set_updated_at();

create index if not exists idx_academic_items_student_id on public.academic_items (student_id);
create index if not exists idx_academic_items_course_id on public.academic_items (course_id);
create index if not exists idx_academic_items_due_date on public.academic_items (due_date);
create index if not exists idx_academic_items_student_due_date on public.academic_items (student_id, due_date);
create index if not exists idx_academic_items_status on public.academic_items (status);

-- 6. calendar_connections
create table if not exists public.calendar_connections (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students(id) on delete cascade,
  provider text not null default 'google' check (provider in ('google', 'outlook')),
  calendar_id text not null default 'primary',
  encrypted_access_token text,
  encrypted_refresh_token text,
  token_expiry timestamptz,
  scopes text[] not null default array['https://www.googleapis.com/auth/calendar'],
  connection_status text not null default 'active' check (
    connection_status in ('active', 'revoked', 'expired', 'error')
  ),
  last_busy_sync_at timestamptz,
  error_message text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(student_id, provider, calendar_id)
);

create trigger set_calendar_connections_updated_at
before update on public.calendar_connections
for each row execute function public.set_updated_at();

create index if not exists idx_calendar_connections_student_id on public.calendar_connections (student_id);

-- 7. calendar_busy_blocks
create table if not exists public.calendar_busy_blocks (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students(id) on delete cascade,
  provider text not null default 'google' check (provider in ('google', 'outlook')),
  external_event_id text,
  title text,
  start_time timestamptz not null,
  end_time timestamptz not null,
  is_all_day boolean not null default false,
  source text not null default 'google_calendar',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique(student_id, provider, external_event_id)
);

create index if not exists idx_calendar_busy_blocks_student_time
on public.calendar_busy_blocks (student_id, start_time, end_time);

-- 8. study_plans (composed by Copilot)
create table if not exists public.study_plans (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students(id) on delete cascade,
  status text not null default 'draft' check (
    status in ('draft', 'approved', 'scheduled', 'completed', 'cancelled')
  ),
  start_date date not null,
  end_date date not null,
  goal text,
  summary text,
  reasoning text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (end_date >= start_date)
);

create trigger set_study_plans_updated_at
before update on public.study_plans
for each row execute function public.set_updated_at();

create index if not exists idx_study_plans_student_id on public.study_plans (student_id);
create index if not exists idx_study_plans_student_dates on public.study_plans (student_id, start_date, end_date);
create index if not exists idx_study_plans_status on public.study_plans (status);

-- 9. study_blocks
create table if not exists public.study_blocks (
  id uuid primary key default gen_random_uuid(),
  study_plan_id uuid not null references public.study_plans(id) on delete cascade,
  student_id uuid not null references public.students(id) on delete cascade,
  academic_item_id uuid references public.academic_items(id) on delete set null,
  title text not null,
  description text,
  start_time timestamptz not null,
  end_time timestamptz not null,
  duration_minutes int generated always as (
    greatest(0, floor(extract(epoch from (end_time - start_time)) / 60)::int)
  ) stored,
  status text not null default 'proposed' check (
    status in ('proposed', 'approved', 'scheduled', 'completed', 'missed', 'cancelled', 'rescheduled')
  ),
  google_calendar_event_id text,
  calendar_html_link text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (end_time > start_time)
);

create trigger set_study_blocks_updated_at
before update on public.study_blocks
for each row execute function public.set_updated_at();

create index if not exists idx_study_blocks_study_plan_id on public.study_blocks (study_plan_id);
create index if not exists idx_study_blocks_student_time on public.study_blocks (student_id, start_time, end_time);
create index if not exists idx_study_blocks_academic_item_id on public.study_blocks (academic_item_id);
create index if not exists idx_study_blocks_status on public.study_blocks (status);

-- 10. oauth_states
create table if not exists public.oauth_states (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students(id) on delete cascade,
  provider text not null default 'google' check (provider in ('google', 'outlook')),
  state text unique not null,
  redirect_after_connect text,
  expires_at timestamptz not null,
  used_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists idx_oauth_states_state on public.oauth_states (state);
create index if not exists idx_oauth_states_student_id on public.oauth_states (student_id);

-- 11. agent_action_logs
create table if not exists public.agent_action_logs (
  id uuid primary key default gen_random_uuid(),
  student_id uuid references public.students(id) on delete set null,
  copilot_user_id text,
  action_name text not null,
  request_payload jsonb,
  response_payload jsonb,
  status text not null default 'success' check (status in ('success', 'error')),
  error_message text,
  duration_ms int,
  created_at timestamptz not null default now()
);

create index if not exists idx_agent_action_logs_student_id on public.agent_action_logs (student_id);
create index if not exists idx_agent_action_logs_copilot_user_id on public.agent_action_logs (copilot_user_id);
create index if not exists idx_agent_action_logs_action_name on public.agent_action_logs (action_name);
create index if not exists idx_agent_action_logs_created_at on public.agent_action_logs (created_at);

-- 12. Storage bucket
insert into storage.buckets (
  id, name, public, file_size_limit, allowed_mime_types
)
values (
  'academic-documents',
  'academic-documents',
  false,
  52428800,
  array[
    'application/pdf',
    'text/plain',
    'text/markdown',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  ]
)
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

-- 13. Vector search
create or replace function public.match_document_chunks (
  query_embedding extensions.vector(1536),
  match_student_id uuid,
  match_count int default 5
)
returns table (
  id uuid,
  document_id uuid,
  course_id uuid,
  chunk_text text,
  similarity float
)
language sql stable
as $$
  select
    document_chunks.id,
    document_chunks.document_id,
    document_chunks.course_id,
    document_chunks.chunk_text,
    1 - (document_chunks.embedding <=> query_embedding) as similarity
  from public.document_chunks
  where document_chunks.student_id = match_student_id
    and document_chunks.embedding is not null
  order by document_chunks.embedding <=> query_embedding
  limit match_count;
$$;

-- 14. Row Level Security (service role bypasses; API enforces access)
alter table public.students enable row level security;
alter table public.courses enable row level security;
alter table public.documents enable row level security;
alter table public.document_chunks enable row level security;
alter table public.academic_items enable row level security;
alter table public.calendar_connections enable row level security;
alter table public.calendar_busy_blocks enable row level security;
alter table public.study_plans enable row level security;
alter table public.study_blocks enable row level security;
alter table public.oauth_states enable row level security;
alter table public.agent_action_logs enable row level security;
