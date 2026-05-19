# 4-Day Build Plan: Academic Planning Agent (Copilot Studio Competition)

## Context

This is a **Microsoft Copilot Studio competition entry** with a hard 4-day deadline. The product is an Academic Planning AI Agent (see [1-overview.md](1-overview.md)) where:

- **Copilot Studio is the brain** — proposes, revises, and explains study plans.
- **FastAPI is the Academic Context API** — data + tool layer only (see [2-system_spec.md](2-system_spec.md)).
- **Supabase + pgvector** is the data store (see [3-db_tables.md](3-db_tables.md)).

**Constraints chosen:**
- Demo format: **live agent in Teams/web chat** (with recorded video as backup).
- Calendar: **full Google OAuth + real event creation**.
- Team size: **2–3 people**.

**Risk profile for a 4-day window:**
1. **Copilot Studio reasoning quality** is the #1 unknown — it must read a JSON planning-context and produce a coherent multi-block plan. Mitigation: keep the JSON small, use very explicit agent instructions with worked examples, rehearse one demo scenario.
2. **Google OAuth on Cloud Run** is a known time-sink (redirect URI, token storage, consent screen). Mitigation: stand it up on Day 1 in parallel with everything else.
3. **Live-demo brittleness** — mitigation: pre-record a backup walkthrough on Day 4 morning.

The goal of this plan is to get a working live demo of the vertical slice (paste syllabus → extract → propose plan → approve → create real Google Calendar events) by end of Day 4, with one rehearsed scenario.

---

## Two parallel tracks

**Track A — Backend (1 person, Python-strong):** FastAPI, Supabase, OpenAI extraction, Google Calendar OAuth, Cloud Run deployment.

**Track B — Copilot Studio (1 person, low-code/conversation design):** agent topology, REST tool actions, system prompt, demo polish, recorded backup.

**Track C — Floater (optional 3rd person):** OpenAPI/Swagger conversion, demo script writing, edge-case test, video recording. If solo on this, fold into Track B.

---

## Day 1 — Foundations (parallel)

### Track A (Backend)
- `supabase init` + paste schema from [3-db_tables.md §5](3-db_tables.md) → `supabase db reset` locally → link hosted project → `supabase db push`.
- FastAPI scaffold per [2-system_spec.md §5–§11](2-system_spec.md): `app/main.py`, `app/core/config.py`, `app/core/security.py` (API-key header), `app/db/supabase.py`, `/health`.
- Implement **only two endpoints** today:
  - `POST /copilot/students/upsert`
  - `POST /copilot/documents/ingest-text` (skip file upload entirely — text paste only).
- **Start the Google Cloud OAuth setup in parallel** (don't leave for Day 3): create GCP project, enable Calendar API, create OAuth client, register *both* `http://localhost:8000/calendar/oauth/callback` and a placeholder Cloud Run URL as authorized redirect URIs. Generate Fernet `TOKEN_ENCRYPTION_KEY` for `.env`.
- Deploy a hello-world FastAPI to Cloud Run today (`gcloud run deploy`) so the URL is known and Google's redirect URI can be locked in.

### Track B (Copilot Studio)
- Provision Copilot Studio environment + create the agent shell.
- Read [2-system_spec.md §25–§26](2-system_spec.md) — agent instructions draft.
- Wire **placeholder REST tools** that point at the hello-world Cloud Run URL. Confirm Copilot Studio can call an external API with an `x-copilot-api-key` header. **Prove this works end-to-end today** — it is the highest-risk integration point.
- Sketch the demo conversation script in a doc.

### End-of-Day-1 checkpoint
- Schema in hosted Supabase ✅
- Cloud Run hello-world reachable from Copilot Studio with API-key auth ✅
- Google OAuth client created, redirect URIs registered ✅

---

## Day 2 — Extraction + Planning Context (the brain-fuel)

### Track A
- `POST /copilot/academic-items/extract` — OpenAI structured outputs per [2-system_spec.md §16](2-system_spec.md). Use `gpt-4.1-mini` with the strict JSON schema. No `priority` field.
- `POST /copilot/academic-items/confirm` — simple update.
- **`GET /copilot/planning-context`** — the most important endpoint. Implement assembly only (no scoring, no conflict detection) per [2-system_spec.md §18](2-system_spec.md). Skip `document_context` snippets today — add Day 4 if there's time.
- `POST /copilot/study-plans/save` + `POST /copilot/study-plans/update` — pure persistence.

### Track B
- Refine agent instructions: paste [2-system_spec.md §26](2-system_spec.md) and **add a worked example** in the prompt showing how to read planning-context JSON and convert it to specific time blocks. Copilot Studio's reasoning is more reliable with concrete examples than abstract rules.
- Wire real tool actions in Copilot Studio for the new endpoints. Use the real Cloud Run URL.
- Test live: paste fake syllabus text → extract → confirm → get planning-context → ask Copilot to propose a plan → save.
- **Today's reasoning test:** does Copilot reliably produce a sensible study plan from a 5-item planning-context? If not, tighten the prompt now — don't defer.

### End-of-Day-2 checkpoint
- Full text-only loop works end-to-end *except* calendar events ✅
- Copilot has demonstrated readable plan-reasoning on a test scenario ✅

---

## Day 3 — Google Calendar Integration

### Track A
- `GET /calendar/oauth/start` — generate `state`, save to `oauth_states`, redirect to Google consent.
- `GET /calendar/oauth/callback` — validate state, exchange code, encrypt tokens with Fernet, save to `calendar_connections`.
- `POST /copilot/calendar/sync-busy` — pull busy events into `calendar_busy_blocks`. Update `last_busy_sync_at`.
- `POST /copilot/calendar/create-events` — refuse if plan status != `approved`; create events; save `google_calendar_event_id` and `calendar_html_link` on blocks; flip plan to `scheduled`.
- Lazy-refresh inside `/planning-context`: if `last_busy_sync_at` is older than ~30 min, sync first.

### Track B
- Add the two new tools (`syncCalendarBusyBlocks`, `createGoogleCalendarStudyEvents`) in Copilot Studio.
- Build the **OAuth handoff UX**: Copilot detects `data_warnings` containing `missing_calendar_connection`, shows the student a link to `https://<cloud-run-url>/calendar/oauth/start?copilot_user_id=...`, waits for confirmation, then retries the planning flow.
- Rehearse the full happy path: greet → paste syllabus → confirm items → connect calendar → planning-context → propose plan → approve → create events → show calendar link.

### End-of-Day-3 checkpoint
- Approved plan creates real events on a personal Google Calendar ✅
- One full rehearsed demo run completed ✅

---

## Day 4 — Polish, Backup, Rehearsal

### Morning
- **Record the backup walkthrough video first** (before live tweaks risk breaking things).
- Fix the top 3 rough edges from yesterday's rehearsal.

### Afternoon
- Optional stretch features only if everything is green:
  - `document_context` snippets in planning-context (embeddings + `match_document_chunks`).
  - `/copilot/study-blocks/status` for the "I missed yesterday's block" scenario.
  - Revise-plan demo turn ("I'm busy Wednesday").
- Sanitize logs in `agent_action_logs`. Add a real `COPILOT_API_KEY` for production. Lock down Cloud Run env vars (move secrets to Secret Manager if time).
- Demo dry-runs ×3 with different team members watching.

### End-of-Day-4 checkpoint
- Live agent reproducibly completes the demo scenario ✅
- Backup video recorded ✅
- README in repo with the demo script + setup notes ✅

---

## Aggressive cut list (drop these without hesitation if behind)

1. **File upload.** Text-paste only via `/copilot/documents/ingest-text`. PDF parsing is a Day 3+ headache.
2. **Document context / embeddings.** Skip `document_chunks` writes and `match_document_chunks`. Planning-context's `document_context` array stays empty.
3. **Plan revise demo turn.** Stick to the create-plan happy path if revise is brittle.
4. **Per-block status updates.** Not needed for the headline demo.
5. **Course difficulty + preferred-style fine-tuning.** Hardcode sensible defaults in the seed student.
6. **Multi-student demo.** One seeded `copilot_user_id = "demo-user-1"` is enough.

---

## Critical files (already exist as docs; will be created as code)

- [1-overview.md](1-overview.md) — source of truth for product framing.
- [2-system_spec.md](2-system_spec.md) — backend API contract + Copilot agent instructions.
- [3-db_tables.md](3-db_tables.md) — Supabase schema.

To be created (Track A):
- `academic-planner-api/app/main.py`
- `academic-planner-api/app/api/copilot.py`
- `academic-planner-api/app/services/extraction_service.py`
- `academic-planner-api/app/services/planning_context_service.py`
- `academic-planner-api/app/services/study_plan_service.py`
- `academic-planner-api/app/services/calendar_service.py`
- `academic-planner-api/supabase/migrations/*_init_academic_context_schema.sql`

To be created (Track B):
- Copilot Studio agent topology + system prompt (managed in Copilot Studio, exported to repo as JSON for safekeeping).
- `swagger-v2.json` — OpenAPI converted from FastAPI's `/openapi.json` via `api-spec-converter`.

---

## Demo script (the one we rehearse)

```text
Student: Help me plan my week.
Copilot: I can help. Please paste your syllabus or any deadlines you have.

Student: [pastes a short block with 3 items — project due June 15 worth 20%,
         quiz June 12, midterm June 18]

Copilot: [calls ingestAcademicText → extractAcademicItems]
         I found 3 items: a project, a quiz, and a midterm. Quick check —
         the quiz date wasn't fully clear, can you confirm June 12?

Student: Yes, June 12.

Copilot: [calls confirmAcademicItems → getPlanningContext]
         Got it. I notice your calendar isn't connected yet, so I won't know
         when you're busy. Want to connect Google Calendar?

Student: Yes.

Copilot: Open this link to connect: [oauth start URL]. Let me know when done.

Student: Done.

Copilot: [calls syncCalendarBusyBlocks → getPlanningContext]
         Here's what I'd suggest: the project is heaviest and due first, so
         let's front-load it. Two-hour blocks Wed and Thu evening for the
         project, one hour Fri for quiz review, weekend for exam prep.
         Want me to add these to your calendar?

Student: Yes.

Copilot: [calls saveStudyPlan (status=approved) → createGoogleCalendarStudyEvents]
         Done — 4 study blocks added. Here's your first one: [link].
```

---

## Verification

End-of-build acceptance:
1. From a clean browser session, open the published Copilot Studio agent.
2. Run the demo script above verbatim. All tool calls return 200. Real Google Calendar events appear in the test account.
3. Re-run with a fresh `copilot_user_id` to confirm onboarding works for a new student.
4. Check `agent_action_logs` rows in Supabase Studio — every tool call should be logged, no secrets in payloads.
5. Backup video plays cleanly and shows the same flow.

Smoke tests during development:
- `curl http://localhost:8000/health` returns `{"status":"ok",...}`.
- The local Supabase Studio shows all 11 tables + the `academic-documents` bucket.
- `POST /copilot/students/upsert` with the demo payload from [2-system_spec.md §27](2-system_spec.md) returns a `student_id`.
- `GET /copilot/planning-context?...` returns the expected JSON shape with an empty `existing_study_blocks` and at least one `data_warnings` entry when calendar isn't connected.
