# Academic Context API — Database Documentation

## 1. Purpose

This document defines the Supabase database structure for the Academic Context API.

**Reminder:** Copilot Studio is the brain. This database stores facts and persists Copilot's decisions. There is no `conflicts` table and no priority/score columns, because the backend does not detect conflicts or rank priorities — Copilot does.

The database supports:

```text
- Student profiles
- Courses
- Uploaded academic documents
- Document chunks and embeddings
- Extracted academic requirements (facts only)
- Study plans composed by Copilot
- Study blocks composed by Copilot
- calendar provider connection records (Google Calendar or Outlook Calendar)
- Calendar busy blocks (cached from selected provider)
- OAuth state handling
- Copilot action audit logs
```

This is managed through the Supabase CLI using SQL migrations.

---

## 2. Supabase CLI Workflow

### 2.1 Install prerequisites

```text
- Docker Desktop
- Supabase CLI
- Node.js/npm (optional)
- VS Code
```

Check Supabase CLI:

```bash
supabase --version
```

### 2.2 Initialize Supabase in the backend project

```bash
cd academic-planner-api
supabase init
```

This creates:

```text
supabase/
  config.toml
  migrations/
```

### 2.3 Start local Supabase stack

```bash
supabase start
supabase status
```

### 2.4 Create first migration

```bash
supabase migration new init_academic_context_schema
```

### 2.5 Apply migration locally

```bash
supabase db reset
```

### 2.6 Link to hosted Supabase project

```bash
supabase login
supabase link --project-ref YOUR_PROJECT_REF
```

### 2.7 Push migrations to hosted Supabase

```bash
supabase db push
```

### 2.8 Pull remote changes

```bash
supabase db pull
```

Recommended rule: SQL migrations are the source of truth. Avoid manual remote schema changes.

Migration note for multi-provider support:
- Relax provider checks from `provider in ('google')` to `provider in ('google', 'outlook')` for `calendar_connections`, `calendar_busy_blocks`, and `oauth_states`.

### 2.9 Generate schema diff migration

```bash
supabase db diff -f migration_name
```

---

## 3. Database Design Principles

```text
1. Every student-specific table must include student_id.
2. External user identity comes from copilot_user_id.
3. Do not store raw OAuth tokens from any provider. Store encrypted tokens only.
4. Uploaded files live in Supabase Storage, not directly in Postgres.
5. Document text can be stored in documents.source_text for MVP.
6. Long document text is chunked into document_chunks.
7. Vector embeddings live in document_chunks.embedding.
8. Study plans are drafts until Copilot saves them as approved.
9. Calendar events are created only from approved study blocks.
10. The backend does NOT compute priority scores or store detected conflicts.
11. Copilot API calls are auditable through agent_action_logs.
```

---

## 4. Table Relationship Map

```text
students
  ├── courses
  ├── documents
  │     └── document_chunks
  ├── academic_items
  ├── calendar_connections
  ├── calendar_busy_blocks
  ├── study_plans
  │     └── study_blocks
  ├── oauth_states
  └── agent_action_logs
```

Main relationships:

```text
students.id → courses.student_id
students.id → documents.student_id
students.id → academic_items.student_id
students.id → study_plans.student_id
study_plans.id → study_blocks.study_plan_id
academic_items.id → study_blocks.academic_item_id
documents.id → document_chunks.document_id
documents.id → academic_items.document_id
courses.id → documents.course_id
courses.id → academic_items.course_id
```

---

## 5. Full Initial Migration SQL

Create the migration:

```bash
supabase migration new init_academic_context_schema
```

Paste this SQL into the generated migration file.

```sql
-- =========================================================
-- Academic Context API Initial Schema
-- =========================================================

-- Extensions
create extension if not exists vector with schema extensions;
create extension if not exists pgcrypto;

-- =========================================================
-- Helper function: updated_at
-- =========================================================

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- =========================================================
-- 1. students
-- =========================================================

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

-- =========================================================
-- 2. courses
-- =========================================================

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

-- =========================================================
-- 3. documents
-- =========================================================

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

-- =========================================================
-- 4. document_chunks
-- =========================================================

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

-- =========================================================
-- 5. academic_items
-- =========================================================
-- Factual academic requirements extracted from documents or confirmed by the student.
-- No "priority" column — Copilot decides priority from context.

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

-- =========================================================
-- 6. calendar_connections
-- =========================================================

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

-- =========================================================
-- 7. calendar_busy_blocks
-- =========================================================

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

-- =========================================================
-- 8. study_plans
-- =========================================================
-- Stores study plans COMPOSED BY COPILOT. The backend persists them; it does not generate them.
-- "summary" and "reasoning" are written by Copilot (the brain), not the backend.

create table if not exists public.study_plans (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students(id) on delete cascade,
  status text not null default 'draft' check (
    status in ('draft', 'approved', 'scheduled', 'completed', 'cancelled')
  ),
  start_date date not null,
  end_date date not null,
  goal text,
  summary text,       -- Copilot's natural-language summary
  reasoning text,     -- Copilot's explanation of priorities
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

-- =========================================================
-- 9. study_blocks
-- =========================================================

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

-- =========================================================
-- 10. oauth_states
-- =========================================================

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

-- =========================================================
-- 11. agent_action_logs
-- =========================================================

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

-- =========================================================
-- 12. Storage bucket
-- =========================================================

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

-- =========================================================
-- 13. Vector search function
-- =========================================================

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

-- =========================================================
-- 14. Row Level Security
-- =========================================================
-- For MVP, the backend uses the Supabase service role key.
-- The service role bypasses RLS, so API security is enforced in FastAPI.

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
```

---

## 6. Table-by-Table Documentation

### 6.1 `students`

Stores the student profile used by Copilot and the backend.

| Column                  | Type  | Purpose                                              |
| ----------------------- | ----- | ---------------------------------------------------- |
| `id`                    | uuid  | Internal student ID                                  |
| `copilot_user_id`       | text  | External identifier from Copilot Studio session/user |
| `name`                  | text  | Student display name                                 |
| `email`                 | text  | Student email                                        |
| `timezone`              | text  | Used for due dates and calendar events               |
| `preferred_study_style` | text  | Example: short blocks, deep work, evening study      |
| `preferred_study_times` | jsonb | Availability preferences                             |
| `metadata`              | jsonb | Extra profile info                                   |

Example `preferred_study_times`:

```json
[
  {"day": "weekday", "start": "19:00", "end": "22:00"},
  {"day": "saturday", "start": "09:00", "end": "12:00"}
]
```

### 6.2 `courses`

Stores the student's courses.

| Column             | Type | Purpose                              |
| ------------------ | ---- | ------------------------------------ |
| `student_id`       | uuid | Owner student                        |
| `course_code`      | text | Example: CS101                       |
| `course_name`      | text | Example: Introduction to Programming |
| `term`             | text | Example: 1st Semester 2026           |
| `instructor`       | text | Optional instructor name             |
| `difficulty_level` | int  | 1–5 ranking, used only as a hint surfaced in planning context |
| `color_label`      | text | Optional UI/calendar grouping        |

`difficulty_level` is *informational* — it appears in planning context for Copilot to consider. The backend does not multiply it into a priority score.

### 6.3 `documents`

Stores uploaded or pasted academic materials.

| Column              | Type | Purpose                             |
| ------------------- | ---- | ----------------------------------- |
| `student_id`        | uuid | Owner student                       |
| `course_id`         | uuid | Related course                      |
| `storage_bucket`    | text | Usually academic-documents          |
| `storage_path`      | text | Supabase Storage path               |
| `file_name`         | text | Original filename                   |
| `file_type`         | text | PDF, text, DOCX, etc.               |
| `source_text`       | text | Extracted or pasted text            |
| `processing_status` | text | File processing state               |
| `extraction_status` | text | Academic extraction state           |

### 6.4 `document_chunks`

Stores chunks of document text for semantic search and `document_context` snippets in planning context.

| Column        | Type         | Purpose                           |
| ------------- | ------------ | --------------------------------- |
| `document_id` | uuid         | Parent document                   |
| `student_id`  | uuid         | Owner student                     |
| `course_id`   | uuid         | Related course                    |
| `chunk_index` | int          | Order in source document          |
| `chunk_text`  | text         | Searchable text                   |
| `token_count` | int          | Approximate token count           |
| `page_number` | int          | Optional page number              |
| `embedding`   | vector(1536) | OpenAI embedding vector           |

### 6.5 `academic_items`

Stores extracted academic requirements **as facts**. No priority column.

| Column                | Type        | Purpose                                           |
| --------------------- | ----------- | ------------------------------------------------- |
| `type`                | text        | assignment, exam, quiz, project, etc.             |
| `title`               | text        | Requirement title                                 |
| `description`         | text        | Short explanation                                 |
| `due_date`            | timestamptz | Due date or exam date                             |
| `due_date_confidence` | numeric     | Confidence specifically for the due date          |
| `weight`              | numeric     | Grade weight, if known                            |
| `estimated_hours`     | numeric     | Workload estimate if the source document gave one |
| `confidence_score`    | numeric     | Overall extraction confidence                     |
| `status`              | text        | pending, confirmed, in_progress, completed, cancelled |
| `needs_confirmation`  | boolean     | True if Copilot should confirm with the student   |
| `source_quote`        | text        | Evidence quote from document                      |

**Important rule:** the backend must never invent due dates. If uncertain, set `due_date = null`, `needs_confirmation = true`, and a low `confidence_score`. Copilot then asks the student.

**No `priority` field.** Copilot reasons about priority from `weight`, `estimated_hours`, `due_date`, `difficulty_level`, and the student's preferences.

### 6.6 `calendar_connections`

Stores encrypted calendar provider OAuth tokens.

| Column                    | Type        | Purpose                         |
| ------------------------- | ----------- | ------------------------------- |
| `student_id`              | uuid        | Owner student                   |
| `provider`                | text        | google or outlook               |
| `calendar_id`             | text        | Usually primary                 |
| `encrypted_access_token`  | text        | Encrypted provider access token   |
| `encrypted_refresh_token` | text        | Encrypted provider refresh token  |
| `token_expiry`            | timestamptz | Token expiration                |
| `scopes`                  | text[]      | Granted OAuth scopes            |
| `connection_status`       | text        | active, revoked, expired, error |
| `last_busy_sync_at`       | timestamptz | When busy blocks were last refreshed |

Never store raw provider tokens. Encrypt before saving.

### 6.7 `calendar_busy_blocks`

Cached busy blocks from the selected calendar provider so `/planning-context` can return them without a live API call every time.

| Column              | Type        | Purpose                  |
| ------------------- | ----------- | ------------------------ |
| `external_event_id` | text        | Provider event ID        |
| `title`             | text        | Event title              |
| `start_time`        | timestamptz | Event start              |
| `end_time`          | timestamptz | Event end                |
| `is_all_day`        | boolean     | All-day flag             |
| `source`            | text        | provider-specific source |

Sync behavior for MVP:

```text
1. Copilot calls /copilot/calendar/sync-busy with a date window (or backend does it lazily inside /planning-context if last_busy_sync_at is stale).
2. Backend fetches provider events for the window.
3. Backend upserts them into calendar_busy_blocks.
4. /planning-context returns the cached rows.
```

### 6.8 `study_plans`

Stores plans **composed by Copilot**. The backend persists the plan and Copilot's narrative; it does not generate them.

| Column       | Type  | Purpose                                                    |
| ------------ | ----- | ---------------------------------------------------------- |
| `student_id` | uuid  | Owner student                                              |
| `status`     | text  | draft, approved, scheduled, completed, cancelled            |
| `start_date` | date  | Plan start                                                 |
| `end_date`   | date  | Plan end                                                   |
| `goal`       | text  | Student's planning goal                                    |
| `summary`    | text  | Copilot's natural-language summary                         |
| `reasoning`  | text  | Copilot's explanation of priorities                        |
| `metadata`   | jsonb | Extra metadata                                              |

Status flow:

```text
draft → approved → scheduled → completed
              ↘ cancelled
```

`scheduled` is set after `/copilot/calendar/create-events` succeeds.

### 6.9 `study_blocks`

Stores individual study sessions composed by Copilot.

| Column                     | Type        | Purpose                                                                  |
| -------------------------- | ----------- | ------------------------------------------------------------------------ |
| `study_plan_id`            | uuid        | Parent plan                                                              |
| `academic_item_id`         | uuid        | Related requirement (optional)                                            |
| `title`                    | text        | Study block title (Copilot writes it)                                     |
| `description`              | text        | What the student should do (Copilot writes it)                            |
| `start_time`               | timestamptz | Block start                                                              |
| `end_time`                 | timestamptz | Block end                                                                |
| `duration_minutes`         | int         | Generated                                                                |
| `status`                   | text        | proposed, approved, scheduled, completed, missed, cancelled, rescheduled |
| `google_calendar_event_id` | text        | Created provider event ID (legacy field name)                            |
| `calendar_html_link`       | text        | Calendar provider link                                                   |

Status flow:

```text
proposed → approved → scheduled → completed
                          ↓
                       missed → rescheduled
```

### 6.10 `oauth_states`

Stores temporary state records for calendar provider OAuth.

| Column                   | Type        | Purpose                            |
| ------------------------ | ----------- | ---------------------------------- |
| `student_id`             | uuid        | Student connecting selected calendar provider |
| `provider`               | text        | google or outlook                 |
| `state`                  | text        | Random secure OAuth state          |
| `redirect_after_connect` | text        | Optional return URL                |
| `expires_at`             | timestamptz | Expiration time (10–15 min)        |
| `used_at`                | timestamptz | Set after callback succeeds        |

### 6.11 `agent_action_logs`

Audit log of backend actions triggered by Copilot Studio.

| Column             | Type  | Purpose                           |
| ------------------ | ----- | --------------------------------- |
| `copilot_user_id`  | text  | Copilot-side user/session ID      |
| `student_id`       | uuid  | Internal student ID, if available |
| `action_name`      | text  | Backend action called             |
| `request_payload`  | jsonb | Request body, sanitized           |
| `response_payload` | jsonb | Response body, sanitized          |
| `status`           | text  | success or error                  |
| `error_message`    | text  | Error detail if failed            |
| `duration_ms`      | int   | Execution time                    |

Do not log secrets, raw OAuth tokens, service role keys, or private files.

---

## 7. Storage Bucket Design

Bucket name: `academic-documents`
Access: private
Max file size for MVP: 50 MB
Allowed mime types: `application/pdf`, `text/plain`, `text/markdown`, `application/msword`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`

Recommended storage path format:

```text
students/{student_id}/courses/{course_id}/{document_id}/{file_name}
```

---

## 8. RLS Strategy

For MVP, the FastAPI backend uses the Supabase service role key.

```text
- The backend is the only database client.
- Copilot Studio never talks directly to Supabase.
- RLS is enabled, but the service role bypasses it.
```

Later, if we build a direct student web portal, add real RLS policies based on Supabase Auth.

---

## 9. Backend Access Pattern

```text
1. Receive copilot_user_id from Copilot Studio.
2. Find or create student in students table.
3. Use students.id as the internal primary ID.
4. Every query after that filters by student_id.
```

Example:

```python
student = supabase.table("students") \
    .select("*") \
    .eq("copilot_user_id", copilot_user_id) \
    .single() \
    .execute()
```

---

## 10. Recommended Migration File Split

```text
001_init_extensions_and_helpers.sql
002_create_core_tables.sql       (students, courses, documents, document_chunks)
003_create_academic_items.sql
004_create_calendar_tables.sql   (calendar_connections, calendar_busy_blocks, oauth_states)
005_create_planning_tables.sql   (study_plans, study_blocks)
006_create_vector_search_function.sql
007_create_storage_bucket.sql
008_enable_rls.sql
009_create_agent_action_logs.sql
```

A single initial migration is fine for MVP setup.

---

## 11. Supabase CLI Cheat Sheet

```bash
supabase start
supabase stop
supabase status
supabase migration new migration_name
supabase db reset
supabase link --project-ref YOUR_PROJECT_REF
supabase db push
supabase db pull
supabase db diff -f migration_name
supabase gen types typescript --linked > types/supabase.ts
```

---

## 12. Seed Data for Local Testing

Create `supabase/seed.sql`:

```sql
insert into public.students (
  copilot_user_id, name, email, timezone,
  preferred_study_style, preferred_study_times
)
values (
  'demo-user-1',
  'Demo Student',
  'demo@example.com',
  'Asia/Manila',
  'short focused blocks',
  '[{"day":"weekday","start":"19:00","end":"22:00"}]'::jsonb
)
on conflict (copilot_user_id) do nothing;
```

Apply with `supabase db reset`.

---

## 13. Example Queries

### Get upcoming academic items (used by /planning-context)

```sql
select
  ai.id,
  c.course_code,
  c.course_name,
  c.difficulty_level,
  ai.type,
  ai.title,
  ai.description,
  ai.due_date,
  ai.due_date_confidence,
  ai.weight,
  ai.estimated_hours,
  ai.confidence_score,
  ai.status,
  ai.needs_confirmation,
  ai.source_quote
from public.academic_items ai
left join public.courses c on c.id = ai.course_id
where ai.student_id = :student_id
  and ai.status in ('pending', 'confirmed', 'in_progress')
  and (ai.due_date is null or ai.due_date between :window_start and :window_end)
order by ai.due_date asc nulls last;
```

### Get calendar busy blocks for a window

```sql
select start_time, end_time, title, is_all_day, external_event_id
from public.calendar_busy_blocks
where student_id = :student_id
  and end_time >= :window_start
  and start_time <= :window_end
order by start_time;
```

### Get existing study blocks for a window

```sql
select sb.id, sb.title, sb.start_time, sb.end_time, sb.status,
       sb.academic_item_id, sp.status as plan_status
from public.study_blocks sb
join public.study_plans sp on sp.id = sb.study_plan_id
where sb.student_id = :student_id
  and sb.end_time >= :window_start
  and sb.start_time <= :window_end
order by sb.start_time;
```

### Search relevant document chunks

```sql
select *
from public.match_document_chunks(:query_embedding, :student_id, 5);
```

### Build data_warnings (low-confidence items)

```sql
select id, title, due_date, confidence_score, needs_confirmation
from public.academic_items
where student_id = :student_id
  and (confidence_score < 0.7 or needs_confirmation = true or due_date is null)
  and status in ('pending', 'confirmed');
```

The backend converts this row set into the `data_warnings` array. It does **not** decide whether the workload is too much — that's Copilot's job.

---

## 14. Data Lifecycle

### Academic document flow

```text
1. Student provides academic text or uploads file.
2. Backend creates documents row.
3. Backend extracts text if file-based.
4. Backend chunks text + creates embeddings.
5. Backend stores chunks in document_chunks.
6. Copilot calls extractAcademicItems → backend extracts factual items via OpenAI.
7. Items saved to academic_items.
8. Copilot asks student to confirm uncertain items → confirmAcademicItems updates them.
```

### Study planning flow

```text
1. Copilot calls /copilot/planning-context for the window.
2. Backend assembles facts and returns them.
3. Copilot reasons about the plan and proposes blocks to the student.
4. Student approves.
5. Copilot calls /copilot/study-plans/save with status="approved" and its composed blocks.
6. Copilot calls /copilot/calendar/create-events.
7. Backend creates calendar provider events.
8. Backend marks plan + blocks as scheduled and saves the provider event id (`google_calendar_event_id`, legacy name).
9. Later: Copilot calls /copilot/study-plans/update or /copilot/study-blocks/status as the student's situation changes.
```

---

## 15. API-to-Table Mapping

| API Endpoint                            | Tables Used                                                                  |
| --------------------------------------- | ---------------------------------------------------------------------------- |
| `/copilot/students/upsert`              | `students`                                                                   |
| `/copilot/documents/ingest-text`        | `students`, `courses`, `documents`, `document_chunks`                        |
| `/copilot/academic-items/extract`       | `documents`, `courses`, `academic_items`, `agent_action_logs`                |
| `/copilot/academic-items/confirm`       | `academic_items`                                                             |
| `/copilot/planning-context`             | `students`, `courses`, `academic_items`, `calendar_busy_blocks`, `study_blocks`, `document_chunks` |
| `/copilot/study-plans/save`             | `study_plans`, `study_blocks`                                                |
| `/copilot/study-plans/update`           | `study_plans`, `study_blocks`                                                |
| `/copilot/study-blocks/status`          | `study_blocks`                                                               |
| `/copilot/calendar/create-events`       | `calendar_connections`, `study_plans`, `study_blocks`                        |
| `/copilot/calendar/sync-busy`           | `calendar_connections`, `calendar_busy_blocks`                               |
| `/calendar/oauth/start`                 | `students`, `oauth_states`                                                   |
| `/calendar/oauth/callback`              | `oauth_states`, `calendar_connections`                                       |

---

## 16. Development Checklist

```text
[ ] Install Supabase CLI
[ ] Run supabase init
[ ] Run supabase start
[ ] Create init migration
[ ] Paste schema SQL
[ ] Run supabase db reset
[ ] Confirm tables in local Supabase Studio
[ ] Add local Supabase URL/service role key to .env
[ ] Connect FastAPI Supabase client
[ ] Test /copilot/students/upsert
[ ] Test /copilot/documents/ingest-text
[ ] Test /copilot/academic-items/extract
[ ] Test /copilot/planning-context
[ ] Test /copilot/study-plans/save
[ ] Link hosted Supabase project
[ ] Run supabase db push
[ ] Confirm tables in hosted Supabase dashboard
```

---

## 17. First Tables to Build and Test

Build these first:

```text
1. students
2. courses
3. documents
4. academic_items
5. study_plans
6. study_blocks
```

Then add:

```text
7. document_chunks
8. calendar_connections
9. calendar_busy_blocks
10. oauth_states
11. agent_action_logs
```

---

## 18. Non-Negotiable Database Rules

```text
1. Do not store API keys in the database.
2. Do not store raw OAuth tokens from any provider.
3. Do not allow public access to academic documents.
4. Do not create calendar events from draft (non-approved) study plans.
5. Do not trust Copilot-provided IDs without resolving them to student_id.
6. Do not return records without filtering by student_id.
7. Store confidence scores for AI-extracted academic items.
8. Keep source_quote when possible for traceability.
9. Do NOT add priority-score or conflict columns. Copilot reasons; the DB stores facts.
10. Store action logs, but sanitize sensitive payloads.
11. Keep SQL migrations in Git.
```

---

## 19. Next Step

In VS Code, run:

```bash
supabase init
supabase start
supabase migration new init_academic_context_schema
```

Paste the SQL from section 5 into the generated migration file. Then:

```bash
supabase db reset
```

Confirm the tables in local Supabase Studio.
