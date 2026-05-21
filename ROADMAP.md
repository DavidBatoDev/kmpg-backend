# Roadmap — Academic Context API (kmpg-backend)

Living plan for backend delivery. **Copilot Studio is the brain; this API is data + tools only.** See [AGENTS.md](AGENTS.md) for agent rules and `documentation/` for full specs.

**Last updated:** May 2026 (boilerplate phase)

---

## Progress at a glance

| Phase | Focus | Status |
|-------|--------|--------|
| 0 | Repo scaffold & FastAPI boilerplate | ✅ Done |
| 1 | Supabase schema + student/document APIs | 🟡 Partial |
| 2 | Extraction + planning context | ⬜ Not started |
| 3 | Study plans persistence | ⬜ Not started |
| 4 | Google Calendar OAuth + events | ⬜ Not started |
| 5 | Copilot Studio connector + demo | ⬜ Not started |
| 6 | Stretch & polish | ⬜ Backlog |

---

## Architecture (backend file plot)

```text
app/api/       → HTTP routes (thin)
app/schemas/   → Pydantic contracts
app/services/  → Business logic
app/db/        → Supabase client
app/core/      → config, API key auth
app/utils/     → time, text chunking
supabase/migrations/ → SQL ✅ (apply with db push / db reset)
```

**Request flow:** `api` → `service` → Supabase (+ OpenAI / Google in services).

---

## Phase 0 — Foundation ✅

**Goal:** Runnable API skeleton, OpenAPI docs, tests, deploy shell.

| Task | Status | Notes |
|------|--------|-------|
| FastAPI `app/main.py` + CORS | ✅ | |
| `GET /health`, `GET /` | ✅ | |
| `app/core/config.py` + `.env.example` | ✅ | |
| `app/core/security.py` (`x-copilot-api-key`) | ✅ | |
| All `/copilot/*` routes wired | ✅ | |
| Pydantic schemas (`app/schemas/copilot.py`) | ✅ | |
| Service stubs + student/document services | ✅ | |
| `requirements.txt`, `Dockerfile`, `.gitignore` | ✅ | |
| `tests/test_health.py` | ✅ | 4 tests passing |
| [AGENTS.md](AGENTS.md) | ✅ | |

**Run locally:**

```powershell
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

---

## Phase 1 — Database & core data APIs 🟡

**Goal:** Supabase is source of truth; student onboarding + text ingest work end-to-end.

| Task | Status | Owner / files |
|------|--------|----------------|
| `supabase init` + migration from [documentation/3-db_tables.md](documentation/3-db_tables.md) §5 | ✅ | `supabase/migrations/20260521120000_init_academic_context_schema.sql` |
| Setup guide + MCP | ✅ | [documentation/7-supabase-setup-and-mcp.md](documentation/7-supabase-setup-and-mcp.md) |
| Link hosted project + `supabase db push` | ⬜ | |
| Apply migrations to hosted Supabase (via MCP) | ✅ | Project `yltcmogqavtwvxvxmqxq` — align `.env` + `mcp.json` |
| Configure `.env` (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`) | ⬜ | Must match MCP project |
| Verify `GET /health` → `supabase_configured: true` | ⬜ | |
| Seed `demo-user-1` | ✅ | 1 row in `students` |
| `POST /copilot/students/upsert` | ✅ | `student_service.py` |
| `POST /copilot/documents/ingest-text` | ✅ | `document_service.py` |
| Seed `demo-user-1` for local demo | ✅ | `supabase/seed.sql` |
| Integration tests for upsert + ingest | ⬜ | `tests/` |
| `agent_action_logs` on Copilot calls | ⬜ | middleware or service helper |

**Exit criteria:** Curl upsert + ingest returns real UUIDs in Supabase Studio.

---

## Phase 2 — Extraction & planning context ⬜

**Goal:** Copilot can load factual deadlines and warnings for a date window.

| Task | Status | Owner / files |
|------|--------|----------------|
| OpenAI structured extraction schema (no `priority`) | ⬜ | `extraction_service.py` |
| `POST /copilot/academic-items/extract` | ⬜ | document → `academic_items` |
| `POST /copilot/academic-items/confirm` | ⬜ | low-confidence updates |
| `GET /copilot/planning-context` | ⬜ | `planning_context_service.py` |
| Assemble: student, courses, items, busy blocks, study blocks | ⬜ | |
| Build `data_warnings` (objective gaps only) | ⬜ | no conflict scoring |
| Optional: lazy calendar sync inside planning-context | ⬜ | defer to Phase 4 |

**Exit criteria:** Planning-context JSON matches spec shape; Copilot can reason on real data in Studio.

**References:** [documentation/2-system_spec.md](documentation/2-system_spec.md) §13.3–13.5, §16–18

---

## Phase 3 — Study plans ⬜

**Goal:** Persist Copilot-composed blocks; no backend-generated plans.

| Task | Status | Owner / files |
|------|--------|----------------|
| `POST /copilot/study-plans/save` | ⬜ | `study_plan_service.py` |
| `POST /copilot/study-plans/update` | ⬜ | `blocks_replace` |
| Status flow: `draft` → `approved` | ⬜ | |
| Resolve `copilot_user_id` → `student_id` on every write | ⬜ | |
| `POST /copilot/study-blocks/status` | ⬜ | stretch |

**Exit criteria:** Save plan from curl; rows visible in `study_plans` + `study_blocks`.

---

## Phase 4 — Google Calendar ⬜

**Goal:** Approved plans become real calendar events; busy blocks feed planning context.

| Task | Status | Owner / files |
|------|--------|----------------|
| GCP project + Calendar API + OAuth client | ⬜ | |
| Register redirect URIs (localhost + Cloud Run) | ⬜ | |
| `TOKEN_ENCRYPTION_KEY` (Fernet) | ⬜ | |
| `GET /calendar/oauth/start` | ⬜ | `calendar.py` + `calendar_service.py` |
| `GET /calendar/oauth/callback` | ⬜ | `oauth_states`, `calendar_connections` |
| `POST /copilot/calendar/sync-busy` | ⬜ | `calendar_busy_blocks` |
| `POST /copilot/calendar/create-events` | ⬜ | refuse if plan ≠ `approved` |
| Store `google_calendar_event_id` on blocks | ⬜ | plan → `scheduled` |

**Exit criteria:** Demo account shows study blocks on Google Calendar after approval.

---

## Phase 5 — Deploy & Copilot Studio ⬜

**Goal:** Live agent calls production API with Swagger 2 connector.

| Task | Status | Notes |
|------|--------|-------|
| Deploy to Google Cloud Run | ⬜ | `Dockerfile` ready |
| Secrets in Secret Manager (prod) | ⬜ | |
| Export `/openapi.json` → Swagger 2.0 | ⬜ | `api-spec-converter` |
| Upload connector to Copilot Studio | ⬜ | `x-copilot-api-key` |
| Tool descriptions per spec §25 | ⬜ | |
| Agent instructions per spec §26 + worked example | ⬜ | Track B |
| End-to-end demo script rehearsal | ⬜ | [documentation/4-build_plan.md](documentation/4-build_plan.md) |

**Exit criteria:** Published Copilot completes MVP vertical slice against Cloud Run.

---

## MVP vertical slice (definition of done)

```text
Student asks Copilot → paste syllabus
  → ingestAcademicText → extractAcademicItems → confirm (if needed)
  → getPlanningContext
  → [Copilot proposes plan in chat]
  → saveStudyPlan (approved) → createGoogleCalendarStudyEvents
```

---

## 4-day sprint alignment (hackathon)

Maps to [documentation/4-build_plan.md](documentation/4-build_plan.md):

| Day | Backend focus |
|-----|----------------|
| **Day 1** | Phase 1 + Cloud Run hello-world + Google OAuth client created |
| **Day 2** | Phase 2 + Phase 3 (text loop without calendar) |
| **Day 3** | Phase 4 full calendar path |
| **Day 4** | Phase 5 polish, backup video, dry-runs |

---

## Stretch / backlog (drop if behind)

| Item | Phase | Priority |
|------|-------|----------|
| `document_context` + embeddings + `match_document_chunks` | 6 | Low |
| Multipart file upload (`/documents/upload`) | 6 | Low |
| Plan revise demo (“busy Wednesday”) | 6 | Medium |
| Per-block status updates | 6 | Low |
| Microsoft Entra ID instead of API key | 6 | Post-MVP |
| RLS policies for future student portal | 6 | Post-MVP |

**Aggressive cut list:** file upload, embeddings, revise turn, per-block status, multi-student demo.

---

## Endpoint checklist

| Endpoint | Phase | Status |
|----------|-------|--------|
| `GET /health` | 0 | ✅ |
| `POST /copilot/students/upsert` | 1 | ✅ (needs Supabase) |
| `POST /copilot/documents/ingest-text` | 1 | ✅ (needs Supabase) |
| `POST /copilot/academic-items/extract` | 2 | ⬜ 501 |
| `POST /copilot/academic-items/confirm` | 2 | ⬜ 501 |
| `GET /copilot/planning-context` | 2 | ⬜ 501 |
| `POST /copilot/study-plans/save` | 3 | ⬜ 501 |
| `POST /copilot/study-plans/update` | 3 | ⬜ 501 |
| `POST /copilot/study-blocks/status` | 3 | ⬜ 501 |
| `POST /copilot/calendar/sync-busy` | 4 | ⬜ 501 |
| `POST /copilot/calendar/create-events` | 4 | ⬜ 501 |
| `GET /calendar/oauth/start` | 4 | ⬜ stub |
| `GET /calendar/oauth/callback` | 4 | ⬜ stub |
| `POST /documents/upload` | 6 | ⬜ stub |

---

## Documentation index

| Doc | Purpose |
|-----|---------|
| [AGENTS.md](AGENTS.md) | AI agent + contributor rules |
| [documentation/1-overview.md](documentation/1-overview.md) | Product vision |
| [documentation/2-system_spec.md](documentation/2-system_spec.md) | API contract, OpenAI, Copilot wiring |
| [documentation/3-db_tables.md](documentation/3-db_tables.md) | Supabase schema SQL |
| [documentation/4-build_plan.md](documentation/4-build_plan.md) | 4-day team plan + demo script |

---

## Non-negotiables (do not slip)

1. Backend does **not** propose study strategy or score priorities.
2. No `priority` field on academic items.
3. No invented due dates — confirm via Copilot when uncertain.
4. Calendar events only for **approved** plans.
5. Every query scoped by `student_id` from `copilot_user_id`.
6. Never commit `.env` or expose service role / API keys.

---

## Suggested next action

**Start Phase 1:** run `supabase init`, add migration from `documentation/3-db_tables.md`, configure `.env`, then test `POST /copilot/students/upsert` against local Supabase.
