# AGENTS.md — Academic Context API (kmpg-backend)

This file is the **agent spec** for Cursor Composer and other coding agents working in this repo. Read it before writing or changing code.

**Extended docs** (human-oriented, longer): [`documentation/1-overview.md`](documentation/1-overview.md), [`documentation/2-system_spec.md`](documentation/2-system_spec.md), [`documentation/3-db_tables.md`](documentation/3-db_tables.md), [`documentation/4-build_plan.md`](documentation/4-build_plan.md).

---

## What this repo is

**Academic Context API** — a Python/FastAPI backend for a Microsoft Copilot Studio **Academic Planning Agent** (hackathon / KPMG competition).

| Layer | Role |
|-------|------|
| **Microsoft Copilot Studio** | Brain: conversation, study plans, priorities, conflict reasoning, student-facing advice |
| **This API (FastAPI)** | Data + tools: storage, extraction, planning context, persist Copilot plans, calendar provider execution (Google Calendar or Outlook Calendar) |
| **Supabase** | Postgres + pgvector + Storage (source of truth) |
| **OpenAI (backend only)** | Structured extraction + embeddings — **not** a planner |
| **Calendar Providers** | OAuth + create study events after student approval (Google Calendar or Outlook Calendar) |

**Product rule:** This is a **study planning** assistant, not an assignment-writing tool. Do not implement features that complete coursework for students.

---

## Non-negotiable boundaries (do not violate)

1. **Copilot is the brain.** The backend returns **facts** and **persists/executes** Copilot decisions. It does **not**:
   - Recommend study strategy or write plan narratives
   - Score priorities or rank conflicts
   - Advise the student directly
   - Revise plans autonomously

2. **No `priority` field** on academic items or in extraction schemas. Copilot infers priority from weight, due dates, hours, preferences.

3. **No `conflicts` table** or conflict-detection logic in the backend. `data_warnings` = objective gaps only (low confidence, missing calendar, null due dates).

4. **Never invent due dates.** If unclear: `due_date = null`, `needs_confirmation = true`, low `confidence_score`, add `clarifying_questions`.

5. **Calendar events only after approval:** Refuse `POST /copilot/calendar/create-events` unless the study plan `status` is `approved`, regardless of provider (`google` or `outlook`).

6. **Secrets:** Never commit `.env`. Never expose Supabase service role key, OpenAI key, Google client secret, or Outlook/Microsoft client secret to clients or Copilot.

7. **OpenAI in backend:** Extraction and embeddings only. System prompts must say: extract facts, do not recommend strategy.

8. **Identity:** Every query filters by `student_id` resolved from `copilot_user_id`. Never trust IDs without resolving to the owning student.

---

## MVP vertical slice (build this first)

```text
Paste syllabus text → ingest → extract academic items → confirm if needed
→ GET planning-context → [Copilot proposes plan] → save study plan (approved)
→ create calendar provider events
```

**Defer unless time:** file upload/PDF parsing, embeddings/`document_context`, plan-revise demo, per-block status, multi-student polish.

---

## Target project layout

Code lives under `app/` at repo root (not necessarily nested in `academic-planner-api/`):

```text
app/
  main.py
  api/
    health.py
    documents.py
    copilot.py          # all /copilot/* routes
  core/
    config.py
    security.py         # x-copilot-api-key
  db/
    supabase.py
  schemas/
    copilot.py
  services/
    student_service.py
    document_service.py
    extraction_service.py
    embedding_service.py
    planning_context_service.py   # assembly only
    study_plan_service.py
    calendar_service.py
    storage_service.py
  utils/
    time.py
    text.py
supabase/migrations/    # schema from documentation/3-db_tables.md
tests/
requirements.txt
Dockerfile
.env.example
```

**Do not add:** `planning_service.py`, `conflict_service.py`, or any “AI planner” service.

---

## Copilot-facing API contract

All `/copilot/*` routes require header: `x-copilot-api-key`.

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/copilot/students/upsert` | Profile + preferences |
| POST | `/copilot/documents/ingest-text` | Store pasted academic text (MVP: no file upload) |
| POST | `/copilot/academic-items/extract` | OpenAI structured extraction → `academic_items` |
| POST | `/copilot/academic-items/confirm` | Student corrections after low-confidence items |
| GET | `/copilot/planning-context` | **Main brain-fuel** — assemble facts for a date window |
| POST | `/copilot/study-plans/save` | Persist Copilot-composed blocks (`draft` \| `approved`) |
| POST | `/copilot/study-plans/update` | Replace blocks when Copilot revises |
| POST | `/copilot/study-blocks/status` | completed / missed / etc. (stretch) |
| POST | `/copilot/calendar/create-events` | provider events for **approved** plan only |
| POST | `/copilot/calendar/sync-busy` | Cache busy blocks |
| GET | `/calendar/oauth/start` | OAuth redirect (not under `/copilot`), provider-aware via `provider` query |
| GET | `/calendar/oauth/callback` | Token exchange + encrypted storage |
| GET | `/health` | Liveness |

**Planning context response shape** (backend assembles; Copilot reasons):

```json
{
  "student": {},
  "courses": [],
  "academic_items": [],
  "calendar_busy_blocks": [],
  "existing_study_blocks": [],
  "document_context": [],
  "data_warnings": []
}
```

Request/response examples and Pydantic models: [`documentation/2-system_spec.md`](documentation/2-system_spec.md) §13–§15.

---

## Database (Supabase)

- Schema SQL: [`documentation/3-db_tables.md`](documentation/3-db_tables.md) §5
- Migrations are source of truth; use `supabase migration` / `supabase db push`
- Backend uses **service role** only (Copilot never talks to Supabase directly)
- Key tables: `students`, `courses`, `documents`, `document_chunks`, `academic_items`, `study_plans`, `study_blocks`, `calendar_connections`, `calendar_busy_blocks`, `oauth_states`, `agent_action_logs`
- Encrypt provider tokens (Fernet); log actions in `agent_action_logs` without secrets

---

## Implementation order

When adding code, follow this sequence unless the user asks otherwise:

1. FastAPI + `/health` + config + API-key security + Supabase client  
2. Supabase migration (core tables)  
3. `/copilot/students/upsert`, `/copilot/documents/ingest-text`  
4. OpenAI extraction + `/copilot/academic-items/extract` + `/confirm`  
5. `/copilot/planning-context` (assembly only)  
6. `/copilot/study-plans/save` and `/update`  
7. Provider OAuth (Google/Outlook) + `/copilot/calendar/create-events` (+ optional `sync-busy`)  
8. OpenAPI → Swagger 2.0 for Copilot Studio custom connector  

4-day schedule: [`documentation/4-build_plan.md`](documentation/4-build_plan.md).

---

## Environment variables

Copy `.env.example` → `.env`. Required keys (see spec for full list):

- `COPILOT_API_KEY`
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_STORAGE_BUCKET`
- `OPENAI_API_KEY`, `OPENAI_MODEL`, embedding settings
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`
- `OUTLOOK_CLIENT_ID`, `OUTLOOK_CLIENT_SECRET`, `OUTLOOK_REDIRECT_URI` (when Outlook is enabled)
- `TOKEN_ENCRYPTION_KEY` (Fernet)

---

## Commands

```bash
# Windows PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
# Docs: http://localhost:8000/docs

supabase start
supabase db reset
supabase db push

# Copilot connector (after deploy)
curl http://localhost:8000/openapi.json -o openapi.json
# Convert OpenAPI 3 → Swagger 2 for Copilot Studio (api-spec-converter)
```

Default timezone for dates: **`Asia/Manila`** unless student profile overrides.

Calendar mode: Copilot must ask provider preference first (`google` or `outlook`) before connect/sync/create calls.

---

## Code conventions

- **Python 3.11+**, FastAPI, Pydantic v2, `pydantic-settings` for config
- Thin routers in `app/api/`; business logic in `app/services/`
- Use structured OpenAI outputs with **strict JSON schema** for extraction (no priority field)
- `planning_context_service`: load and merge data; build `data_warnings`; **no** scoring or conflict labels
- `study_plan_service`: persist blocks exactly as Copilot sends them
- Return clear JSON messages for Copilot tool UX (`message`, ids, counts)
- Prefer explicit HTTP errors (`401` bad API key, `404` student not found) over silent failures

---

## OpenAI extraction schema (facts only)

Allowed `type` values: `assignment`, `exam`, `quiz`, `project`, `reading`, `presentation`, `lab`, `other`.

Extract: `course_code`, `course_name`, `title`, `description`, `due_date`, `weight`, `estimated_hours`, `confidence_score`, `source_quote`. Set `needs_confirmation` when confidence &lt; 0.7 or date ambiguous.

Full schema: [`documentation/2-system_spec.md`](documentation/2-system_spec.md) §16.

---

## Copilot Studio integration (out of repo)

- Import Swagger 2.0 from `/openapi.json`
- Security: API key header `x-copilot-api-key`
- Tool names: `upsertStudentProfile`, `ingestAcademicText`, `extractAcademicItems`, `confirmAcademicItems`, `getPlanningContext`, `saveStudyPlan`, `updateStudyPlan`, `createCalendarStudyEvents`, `syncCalendarBusyBlocks`
- Agent instructions draft: [`documentation/2-system_spec.md`](documentation/2-system_spec.md) §26

Agents working **only on backend** should not change Copilot prompts unless asked; reference §26 when documenting expected agent behavior.

---

## Testing & verification

- `GET /health` → `{"status":"ok","service":"academic-context-api"}`
- Curl examples: [`documentation/2-system_spec.md`](documentation/2-system_spec.md) §27
- Demo script: [`documentation/4-build_plan.md`](documentation/4-build_plan.md) “Demo script”
- After changes: run relevant endpoint with `x-copilot-api-key`; confirm `student_id` scoping in Supabase Studio

---

## What agents should avoid

- Adding “smart planning” or LLM calls that propose schedules in the backend
- Adding priority/conflict columns or endpoints
- Creating calendar events for `draft` plans
- Broad refactors unrelated to the requested task
- Committing secrets or changing git config
- New markdown files unless the user asks

---

## Quick reference: who decides what

| Decision | Owner |
|----------|--------|
| What to study when, block times, explanations | Copilot Studio |
| Extract due dates/weights from documents | Backend + OpenAI |
| Store profile, items, plans, blocks | Backend + Supabase |
| Whether workload is “too much” | Copilot (from planning context) |
| Create calendar provider events | Backend (after Copilot + student approval) |

When in doubt: **if it requires judgment or natural language for the student, it belongs in Copilot, not here.**
