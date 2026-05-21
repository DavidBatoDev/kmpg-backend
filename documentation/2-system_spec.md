# Academic Context API — Backend Documentation

## 1. Purpose

This backend is the **Academic Context API** that serves the Microsoft Copilot Studio Academic Planning Agent.

**Copilot Studio is the brain.** It proposes study plans, revises them, explains priorities, and decides what to do conversationally.

**This backend is the data and tool layer.** It stores student data, processes academic documents, extracts deadlines, returns planning context, saves Copilot-created study plans, and executes approved calendar provider actions. The backend does **not** decide study strategy.

The backend is built in VS Code using Python/FastAPI, deployed as a serverless service on Google Cloud Run, and connected to Microsoft Copilot Studio through REST API actions using an OpenAPI/Swagger specification.

---

## 2. Final Stack

```text
Frontend / Agent (Brain)
- Microsoft Copilot Studio

Backend (Data & Tool Layer)
- Python
- FastAPI
- REST API with OpenAPI schema
- Google Cloud Run serverless deployment

Database
- Supabase Postgres
- pgvector extension

File Storage
- Supabase Storage

AI Utility Layer (Extraction only — not a planner)
- OpenAI API
- Structured Outputs for extraction
- Embeddings for semantic search

Calendar (External Action System)
- Calendar provider APIs (Google Calendar + Outlook Calendar)
- OAuth user connection
```

---

## 3. High-Level Architecture

```text
Student
  ↓
Microsoft Copilot Studio Agent   ← BRAIN
  ↓
REST API Action / Custom Connector
  ↓
FastAPI Academic Context API     ← DATA + TOOLS
  ↓
Supabase Postgres + pgvector + Supabase Storage
  ↓
OpenAI API (extraction utility) + calendar provider APIs (execution)
```

### Responsibility Split

| Layer                     | Responsibility                                                                                                                  |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| **Copilot Studio (brain)** | Conversation, clarifying questions, study plan proposal, plan revision, prioritization narrative, motivational guidance, approval flow |
| **FastAPI backend**       | Storage, document ingestion, fact extraction, planning context retrieval, saving Copilot-created plans, calendar event execution, audit logging |
| Supabase Postgres         | Students, courses, deadlines, study plans, calendar connections                                                                  |
| Supabase Storage          | Syllabi, assignment briefs, uploaded files                                                                                       |
| pgvector                  | Semantic search over document chunks                                                                                             |
| OpenAI                    | Structured extraction from documents, embeddings, optional document summarization for Copilot context                            |
| Calendar providers (Google/Outlook) | Availability sync and creation of approved study events                                                                |

### What the backend does NOT do

```text
- Decide the best study strategy
- Score priorities
- Detect or rank conflicts
- Write the final study plan narrative
- Advise the student directly
- Revise the plan by itself
- Generate motivational guidance
- Explain why the plan is best
```

All of that belongs to Copilot Studio.

---

## 4. MVP Scope

The first working version should prove this flow:

```text
1. Student asks Copilot: "Help me plan my week."
2. Copilot asks for academic inputs.
3. Student provides pasted syllabus text or uploads a document.
4. Backend stores the document.
5. Copilot asks backend to extract academic items.
6. Backend extracts via OpenAI structured output and saves to Supabase.
7. Copilot asks the student to confirm any low-confidence items.
8. Copilot calls GET /copilot/planning-context for the planning window.
9. Backend returns deadlines, busy calendar blocks, preferences, document context, and data warnings.
10. Copilot composes a study plan and explains it to the student.
11. Student approves.
12. Copilot calls POST /copilot/study-plans/save with the blocks it composed.
13. Copilot calls POST /copilot/calendar/create-events to push to the selected calendar provider.
14. Student later says: "I'm busy Wednesday."
15. Copilot composes the revision and calls POST /copilot/study-plans/update.
```

### Build the vertical slice first

```text
Ingest text → Extract items → Return planning context → Save Copilot plan → Create calendar provider events
```

Do not start with every feature. Build this slice end-to-end first.

---

## 5. VS Code Project Setup

### 5.1 Create project folder

```bash
mkdir academic-planner-api
cd academic-planner-api
code .
```

### 5.2 Create virtual environment

```bash
python -m venv .venv
```

Activate it:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

### 5.3 Create base files

```bash
mkdir app app/api app/core app/db app/schemas app/services app/utils sql tests
ni app/__init__.py
ni app/main.py
ni app/core/config.py
ni app/db/supabase.py
ni requirements.txt
ni .env.example
ni .gitignore
ni Dockerfile
```

For macOS/Linux, replace `ni` with `touch`.

---

## 6. Recommended Project Structure

```text
academic-planner-api/
│
├─ app/
│  ├─ main.py
│  ├─ api/
│  │  ├─ health.py
│  │  ├─ documents.py
│  │  └─ copilot.py          ← all Copilot-facing endpoints
│  │
│  ├─ core/
│  │  ├─ config.py
│  │  └─ security.py
│  │
│  ├─ db/
│  │  └─ supabase.py
│  │
│  ├─ schemas/
│  │  └─ copilot.py
│  │
│  ├─ services/
│  │  ├─ student_service.py
│  │  ├─ document_service.py
│  │  ├─ extraction_service.py   ← OpenAI structured extraction (utility)
│  │  ├─ embedding_service.py    ← OpenAI embeddings (utility)
│  │  ├─ planning_context_service.py  ← assembles context for Copilot
│  │  ├─ study_plan_service.py   ← saves Copilot-created plans, no AI logic
│  │  ├─ calendar_service.py     ← provider OAuth (Google/Outlook) + event creation
│  │  └─ storage_service.py
│  │
│  └─ utils/
│     ├─ time.py
│     └─ text.py
│
├─ sql/
│  ├─ 001_init.sql
│  └─ 002_vector_search.sql
│
├─ tests/
│  └─ test_health.py
│
├─ .env.example
├─ .gitignore
├─ Dockerfile
├─ requirements.txt
└─ README.md
```

Note: there is no `planning_service.py` or `conflict_service.py`. Copilot does that work.

---

## 7. Environment Variables

Create `.env.example`:

```env
APP_NAME=Academic Context API
APP_ENV=local
APP_BASE_URL=http://localhost:8000

COPILOT_API_KEY=replace_with_random_long_key

SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=replace_with_service_role_key
SUPABASE_STORAGE_BUCKET=academic-documents

OPENAI_API_KEY=replace_with_openai_key
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=1536

GOOGLE_CLIENT_ID=replace_with_google_oauth_client_id
GOOGLE_CLIENT_SECRET=replace_with_google_oauth_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/calendar/oauth/callback

TOKEN_ENCRYPTION_KEY=replace_with_fernet_key
```

Create your real `.env` locally. Never commit it.

### `.gitignore`

```gitignore
.venv/
__pycache__/
.env
.pytest_cache/
*.pyc
.DS_Store
```

---

## 8. Python Dependencies

Create `requirements.txt`:

```txt
fastapi==0.115.14
uvicorn[standard]==0.35.0
pydantic==2.11.7
pydantic-settings==2.10.1
python-dotenv==1.1.1
supabase==2.16.0
openai==1.93.0
google-api-python-client==2.176.0
google-auth==2.40.3
google-auth-oauthlib==1.2.2
google-auth-httplib2==0.2.0
python-multipart==0.0.20
cryptography==45.0.5
httpx==0.28.1
pytest==8.4.1
```

Install:

```bash
pip install -r requirements.txt
```

---

## 9. FastAPI App Foundation

### `app/core/config.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Academic Context API"
    app_env: str = "local"
    app_base_url: str = "http://localhost:8000"

    copilot_api_key: str

    supabase_url: str
    supabase_service_role_key: str
    supabase_storage_bucket: str = "academic-documents"

    openai_api_key: str
    openai_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1536

    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str

    token_encryption_key: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
```

### `app/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, documents, copilot
from app.core.config import settings

app = FastAPI(
    title="Academic Context API",
    description="Data and tool layer for the Microsoft Copilot Studio Academic Planning Agent. Copilot Studio is the brain; this API serves structured context and executes approved actions.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(documents.router, prefix="/documents", tags=["Documents"])
app.include_router(copilot.router, prefix="/copilot", tags=["Copilot"])
```

### `app/api/health.py`

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "academic-context-api"}
```

Run locally:

```bash
uvicorn app.main:app --reload --port 8000
```

Open:

```text
http://localhost:8000/docs
http://localhost:8000/openapi.json
```

---

## 10. Security for Copilot Studio API Calls

For MVP, protect backend routes with a static API key passed by Copilot Studio in a header.

Later, we can upgrade to OAuth or Microsoft Entra ID.

### `app/core/security.py`

```python
from fastapi import Header, HTTPException, status
from app.core.config import settings


async def verify_copilot_api_key(x_copilot_api_key: str = Header(...)):
    if x_copilot_api_key != settings.copilot_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Copilot API key",
        )
    return True
```

---

## 11. Supabase Client

### `app/db/supabase.py`

```python
from supabase import create_client, Client
from app.core.config import settings


def get_supabase() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
```

Use the service role key only on the server. Do not expose it to Copilot Studio, frontend clients, or browser code.

---

## 12. Database Schema

See `3-db_tables.md` for the full schema. The backend stores students, courses, documents, document chunks, academic items, calendar connections, calendar busy blocks, study plans, study blocks, OAuth states, and audit logs. **There is no `conflicts` table and no priority scoring** — Copilot reasons about conflicts and priorities directly from the planning context.

---

## 13. Copilot-Facing API Endpoints

Copilot Studio calls these endpoints. Each one either **returns structured facts** or **persists / executes a decision Copilot has already made**.

### 13.1 Upsert student profile

```http
POST /copilot/students/upsert
```

Request:

```json
{
  "copilot_user_id": "user-123",
  "name": "Alex Santos",
  "email": "alex@example.com",
  "timezone": "Asia/Manila",
  "preferred_study_style": "short focused blocks",
  "preferred_study_times": [
    {"day": "weekday", "start": "19:00", "end": "22:00"},
    {"day": "saturday", "start": "09:00", "end": "12:00"}
  ]
}
```

Response:

```json
{
  "student_id": "uuid",
  "message": "Student profile saved."
}
```

---

### 13.2 Ingest academic text

```http
POST /copilot/documents/ingest-text
```

Request:

```json
{
  "copilot_user_id": "user-123",
  "course_code": "CS101",
  "course_name": "Introduction to Programming",
  "document_name": "CS101 syllabus pasted text",
  "text": "Course requirements: Assignment 1 due June 12..."
}
```

Response:

```json
{
  "document_id": "uuid",
  "course_id": "uuid",
  "message": "Document text stored and ready for extraction."
}
```

---

### 13.3 Extract academic items

Backend uses OpenAI structured outputs to pull factual items out of a document. No prioritization, no strategy.

```http
POST /copilot/academic-items/extract
```

Request:

```json
{
  "copilot_user_id": "user-123",
  "document_id": "uuid"
}
```

Response:

```json
{
  "items": [
    {
      "id": "uuid",
      "type": "assignment",
      "title": "Final Project Proposal",
      "due_date": "2026-06-15T23:59:00+08:00",
      "weight": 20,
      "estimated_hours": 8,
      "confidence_score": 0.88,
      "needs_confirmation": false,
      "source_quote": "Final Project Proposal due June 15 at 11:59 PM"
    }
  ],
  "clarifying_questions": [],
  "message": "I found 1 academic item."
}
```

Notes:
- `estimated_hours` is a model-extracted estimate where the document gives a hint; otherwise the field can be omitted or left at a small default. The backend does not compute workload strategy.
- No `priority` field. Copilot decides priority from context.

---

### 13.4 Confirm or correct academic items

After Copilot asks the student about low-confidence items, it sends back confirmations or corrections.

```http
POST /copilot/academic-items/confirm
```

Request:

```json
{
  "copilot_user_id": "user-123",
  "items": [
    {
      "id": "uuid",
      "confirmed": true,
      "due_date": "2026-06-15T23:59:00+08:00",
      "weight": 20,
      "estimated_hours": 6
    },
    {
      "id": "uuid",
      "confirmed": false,
      "cancelled_reason": "duplicate"
    }
  ]
}
```

Response:

```json
{
  "updated": 2,
  "message": "Academic items updated."
}
```

---

### 13.5 Get planning context (the main brain-fuel endpoint)

This is the most important endpoint. It returns everything Copilot needs to reason about the week.

```http
GET /copilot/planning-context?copilot_user_id=user-123&start_date=2026-06-10&end_date=2026-06-17
```

Response:

```json
{
  "student": {
    "name": "Alex",
    "timezone": "Asia/Manila",
    "preferred_study_style": "short focused blocks",
    "preferred_study_times": [
      {"day": "weekday", "start": "19:00", "end": "22:00"}
    ]
  },
  "courses": [
    {
      "id": "course-1",
      "course_code": "CS101",
      "course_name": "Introduction to Programming",
      "difficulty_level": 4
    }
  ],
  "academic_items": [
    {
      "id": "item-1",
      "course_code": "CS101",
      "type": "project",
      "title": "Final Project Proposal",
      "due_date": "2026-06-15T23:59:00+08:00",
      "weight": 20,
      "estimated_hours": 8,
      "confidence_score": 0.91,
      "needs_confirmation": false,
      "status": "confirmed"
    }
  ],
  "calendar_busy_blocks": [
    {
      "start_time": "2026-06-12T18:00:00+08:00",
      "end_time": "2026-06-12T20:00:00+08:00",
      "title": "Class"
    }
  ],
  "existing_study_blocks": [],
  "document_context": [
    {
      "course_code": "CS101",
      "snippet": "Project proposals must be 3-5 pages...",
      "source_document_id": "uuid"
    }
  ],
  "data_warnings": [
    {
      "type": "low_confidence_due_date",
      "academic_item_id": "item-7",
      "message": "Quiz 2 due date may need confirmation."
    },
    {
      "type": "missing_calendar_connection",
      "message": "Selected calendar provider is not connected, so busy blocks may be incomplete."
    }
  ]
}
```

`data_warnings` is for objective gaps (low confidence, missing connections). It is **not** a conflict-detection feature — Copilot decides what counts as a workload conflict.

---

### 13.6 Save a Copilot-created study plan

Copilot composes the blocks. The backend persists them as-is.

```http
POST /copilot/study-plans/save
```

Request:

```json
{
  "copilot_user_id": "user-123",
  "start_date": "2026-06-10",
  "end_date": "2026-06-17",
  "status": "approved",
  "goal": "Plan my week around upcoming deadlines",
  "summary": "Project first, quiz review Thursday.",
  "reasoning": "The project is heavier and due first, so we front-load it.",
  "blocks": [
    {
      "academic_item_id": "item-1",
      "title": "Work on CS101 Final Project Proposal",
      "description": "Create outline and draft project objective.",
      "start_time": "2026-06-11T19:00:00+08:00",
      "end_time": "2026-06-11T21:00:00+08:00"
    }
  ]
}
```

Response:

```json
{
  "study_plan_id": "uuid",
  "block_ids": ["uuid", "uuid"],
  "message": "Study plan saved."
}
```

`status` may be `draft` (Copilot is still iterating with the student) or `approved` (student confirmed).

---

### 13.7 Update a saved study plan

Used when Copilot revises a plan (e.g., student is busy Wednesday). The backend replaces or patches blocks as Copilot specifies.

```http
POST /copilot/study-plans/update
```

Request:

```json
{
  "copilot_user_id": "user-123",
  "study_plan_id": "uuid",
  "status": "approved",
  "summary": "Moved Wed block to Thu.",
  "reasoning": "Student is busy Wed evening.",
  "blocks_replace": [
    {
      "academic_item_id": "item-1",
      "title": "Work on CS101 Final Project Proposal",
      "start_time": "2026-06-12T19:00:00+08:00",
      "end_time": "2026-06-12T21:00:00+08:00"
    }
  ]
}
```

`blocks_replace` overwrites the block list. (Add `blocks_patch` later if partial updates are needed.)

Response:

```json
{
  "study_plan_id": "uuid",
  "message": "Study plan updated."
}
```

---

### 13.8 Update a study block's status

Used when the student tells Copilot they completed or missed a block.

```http
POST /copilot/study-blocks/status
```

Request:

```json
{
  "copilot_user_id": "user-123",
  "study_block_id": "uuid",
  "status": "completed"
}
```

Allowed statuses: `proposed`, `approved`, `scheduled`, `completed`, `missed`, `cancelled`, `rescheduled`.

Response:

```json
{
  "study_block_id": "uuid",
  "status": "completed"
}
```

---

### 13.9 Create calendar provider events

After the student approves and Copilot has saved the plan, Copilot asks the backend to push approved blocks to the selected calendar provider.

```http
POST /copilot/calendar/create-events
```

Request:

```json
{
  "copilot_user_id": "user-123",
  "study_plan_id": "uuid",
  "provider": "google"
}
```

Response:

```json
{
  "created_events": [
    {
      "study_block_id": "uuid",
      "calendar_event_id": "event-id",
      "html_link": "https://calendar-provider.example/..."
    }
  ],
  "message": "Study events were added to the selected calendar provider."
}
```

---

### 13.10 Sync calendar busy blocks (optional helper)

Pull busy events from the selected calendar provider into `calendar_busy_blocks` so `/planning-context` can include them.

```http
POST /copilot/calendar/sync-busy
```

Request:

```json
{
  "copilot_user_id": "user-123",
  "start_date": "2026-06-10",
  "end_date": "2026-06-17",
  "provider": "google"
}
```

Response:

```json
{
  "synced": 12,
  "message": "Busy blocks refreshed."
}
```

---

## 14. Pydantic Schemas

### `app/schemas/copilot.py`

```python
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class PreferredStudyTime(BaseModel):
    day: str
    start: str
    end: str


class StudentUpsertRequest(BaseModel):
    copilot_user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    timezone: str = "Asia/Manila"
    preferred_study_style: Optional[str] = None
    preferred_study_times: list[PreferredStudyTime] = []


class IngestTextRequest(BaseModel):
    copilot_user_id: str
    course_code: Optional[str] = None
    course_name: str
    document_name: str
    text: str = Field(min_length=20)


class ExtractAcademicItemsRequest(BaseModel):
    copilot_user_id: str
    document_id: str


class AcademicItemConfirmation(BaseModel):
    id: str
    confirmed: bool
    due_date: Optional[datetime] = None
    weight: Optional[float] = None
    estimated_hours: Optional[float] = None
    cancelled_reason: Optional[str] = None


class ConfirmAcademicItemsRequest(BaseModel):
    copilot_user_id: str
    items: list[AcademicItemConfirmation]


class PlanningContextQuery(BaseModel):
    copilot_user_id: str
    start_date: date
    end_date: date


class StudyBlockInput(BaseModel):
    academic_item_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime


class SaveStudyPlanRequest(BaseModel):
    copilot_user_id: str
    start_date: date
    end_date: date
    status: str = "draft"  # draft | approved
    goal: Optional[str] = None
    summary: Optional[str] = None
    reasoning: Optional[str] = None
    blocks: list[StudyBlockInput]


class UpdateStudyPlanRequest(BaseModel):
    copilot_user_id: str
    study_plan_id: str
    status: Optional[str] = None
    summary: Optional[str] = None
    reasoning: Optional[str] = None
    blocks_replace: Optional[list[StudyBlockInput]] = None


class StudyBlockStatusRequest(BaseModel):
    copilot_user_id: str
    study_block_id: str
    status: str


class CreateCalendarEventsRequest(BaseModel):
    copilot_user_id: str
    study_plan_id: str


class SyncBusyRequest(BaseModel):
    copilot_user_id: str
    start_date: date
    end_date: date
```

---

## 15. Copilot Router Skeleton

### `app/api/copilot.py`

```python
from fastapi import APIRouter, Depends

from app.core.security import verify_copilot_api_key
from app.schemas.copilot import (
    StudentUpsertRequest,
    IngestTextRequest,
    ExtractAcademicItemsRequest,
    ConfirmAcademicItemsRequest,
    SaveStudyPlanRequest,
    UpdateStudyPlanRequest,
    StudyBlockStatusRequest,
    CreateCalendarEventsRequest,
    SyncBusyRequest,
)
from app.services import (
    student_service,
    document_service,
    extraction_service,
    planning_context_service,
    study_plan_service,
    calendar_service,
)

router = APIRouter(dependencies=[Depends(verify_copilot_api_key)])


@router.post("/students/upsert")
def upsert_student(payload: StudentUpsertRequest):
    return student_service.upsert_student(payload)


@router.post("/documents/ingest-text")
def ingest_text(payload: IngestTextRequest):
    return document_service.ingest_text(payload)


@router.post("/academic-items/extract")
def extract_academic_items(payload: ExtractAcademicItemsRequest):
    return extraction_service.extract_and_save_items(payload)


@router.post("/academic-items/confirm")
def confirm_academic_items(payload: ConfirmAcademicItemsRequest):
    return extraction_service.confirm_items(payload)


@router.get("/planning-context")
def planning_context(copilot_user_id: str, start_date: str, end_date: str):
    return planning_context_service.get_context(copilot_user_id, start_date, end_date)


@router.post("/study-plans/save")
def save_study_plan(payload: SaveStudyPlanRequest):
    return study_plan_service.save_plan(payload)


@router.post("/study-plans/update")
def update_study_plan(payload: UpdateStudyPlanRequest):
    return study_plan_service.update_plan(payload)


@router.post("/study-blocks/status")
def study_block_status(payload: StudyBlockStatusRequest):
    return study_plan_service.update_block_status(payload)


@router.post("/calendar/create-events")
def create_calendar_events(payload: CreateCalendarEventsRequest):
    return calendar_service.create_study_events(payload)


@router.post("/calendar/sync-busy")
def sync_busy(payload: SyncBusyRequest):
    return calendar_service.sync_busy_blocks(payload)
```

---

## 16. OpenAI Extraction Design

OpenAI is used in the backend **only** as a structured-extraction utility. It pulls facts out of academic documents. It does not plan or advise.

### Extraction output schema

```json
{
  "courses": [
    {
      "course_code": "CS101",
      "course_name": "Introduction to Programming"
    }
  ],
  "academic_items": [
    {
      "course_code": "CS101",
      "type": "assignment",
      "title": "Final Project Proposal",
      "description": "Submit a project proposal.",
      "due_date": "2026-06-15T23:59:00+08:00",
      "weight": 20,
      "estimated_hours": 8,
      "confidence_score": 0.88,
      "source_quote": "Final Project Proposal due June 15 at 11:59 PM"
    }
  ],
  "clarifying_questions": []
}
```

Note: no `priority` field. The model extracts factual hints (weight, estimated hours when stated, due date, confidence). Copilot decides priority.

### `app/services/extraction_service.py` (extraction call only)

```python
from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.openai_api_key)


ACADEMIC_EXTRACTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "courses": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "course_code": {"type": ["string", "null"]},
                    "course_name": {"type": "string"}
                },
                "required": ["course_code", "course_name"]
            }
        },
        "academic_items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "course_code": {"type": ["string", "null"]},
                    "type": {
                        "type": "string",
                        "enum": ["assignment", "exam", "quiz", "project", "reading", "presentation", "lab", "other"]
                    },
                    "title": {"type": "string"},
                    "description": {"type": ["string", "null"]},
                    "due_date": {"type": ["string", "null"]},
                    "weight": {"type": ["number", "null"]},
                    "estimated_hours": {"type": ["number", "null"]},
                    "confidence_score": {"type": "number"},
                    "source_quote": {"type": ["string", "null"]}
                },
                "required": [
                    "course_code",
                    "type",
                    "title",
                    "description",
                    "due_date",
                    "weight",
                    "estimated_hours",
                    "confidence_score",
                    "source_quote"
                ]
            }
        },
        "clarifying_questions": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["courses", "academic_items", "clarifying_questions"]
}


def call_openai_extraction(text: str, timezone: str = "Asia/Manila") -> dict:
    response = client.responses.create(
        model=settings.openai_model,
        input=[
            {
                "role": "system",
                "content": (
                    "You extract factual academic requirements from syllabi, assignment briefs, "
                    "course outlines, and student-provided academic text. Return ONLY facts grounded "
                    "in the input. Do NOT recommend study strategy or rank priority. "
                    "If a date is ambiguous, set due_date to null and add a clarifying question. "
                    f"Assume timezone: {timezone}."
                )
            },
            {"role": "user", "content": text}
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "academic_extraction",
                "schema": ACADEMIC_EXTRACTION_SCHEMA,
                "strict": True
            }
        }
    )
    return response.output_parsed
```

---

## 17. Embeddings Design

For each document, split text into chunks, generate embeddings, and save chunks to `document_chunks`. Used for `document_context` snippets in `/planning-context`.

### Chunking rule for MVP

```text
- Split into chunks around 800 to 1,200 words.
- Keep overlap of around 100 to 150 words.
- Store document_id, student_id, course_id, chunk_text, and embedding.
```

### `app/services/embedding_service.py`

```python
from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.openai_api_key)


def create_embedding(text: str) -> list[float]:
    response = client.embeddings.create(
        model=settings.openai_embedding_model,
        input=text
    )
    return response.data[0].embedding
```

---

## 18. Planning Context Service

The backend's job for `/planning-context` is **assembly, not reasoning**. It collects facts.

```text
1. Resolve copilot_user_id → student.
2. Load student profile + preferences.
3. Load courses.
4. Load academic_items where due_date is between start_date and end_date,
   or status in (pending, confirmed, in_progress).
5. Load calendar_busy_blocks in the window (refresh from Google if connection exists and last sync is stale).
6. Load existing study_blocks in the window.
7. Load top-N relevant document_chunks for each upcoming item (optional, MVP-skippable).
8. Build data_warnings:
   - any item with confidence_score < 0.7 or needs_confirmation = true
   - missing calendar connection
   - missing preferred_study_times
   - items with null due_date
9. Return the bundle.
```

**The backend does not score priorities, detect deadline clusters, or label conflicts.** Copilot reads the bundle and reasons about it.

---

## 19. Calendar Provider Integration (Google + Outlook)

### OAuth flow

```http
GET /calendar/oauth/start?provider=google&copilot_user_id=user-123
GET /calendar/oauth/callback
```

`/calendar/oauth/start` redirects the student to provider consent.

`/calendar/oauth/callback` receives the authorization code, exchanges it for tokens, encrypts the tokens, and stores them in `calendar_connections`.

### Required OAuth scopes (by provider)

```text
google: https://www.googleapis.com/auth/calendar
outlook: Calendars.ReadWrite
```

### Calendar event format

```python
event = {
    "summary": "Study: CS101 Final Project Proposal",
    "description": "Generated by Academic Planning Agent.",
    "start": {
        "dateTime": "2026-06-11T19:00:00+08:00",
        "timeZone": "Asia/Manila"
    },
    "end": {
        "dateTime": "2026-06-11T21:00:00+08:00",
        "timeZone": "Asia/Manila"
    }
}
```

### Important rule

Only create calendar events after the student approves the plan and Copilot has saved it with `status = "approved"`. The backend should refuse `/calendar/create-events` for draft plans.

---

## 20. Calendar Provider Service Skeleton

### `app/services/calendar_service.py`

```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def build_calendar_service(access_token: str, refresh_token: str, client_id: str, client_secret: str):
    credentials = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/calendar"],
    )
    return build("calendar", "v3", credentials=credentials)


def create_google_event(service, calendar_id: str, block: dict, timezone: str):
    event = {
        "summary": f"Study: {block['title']}",
        "description": block.get("description") or "Generated by Academic Planning Agent.",
        "start": {"dateTime": block["start_time"], "timeZone": timezone},
        "end": {"dateTime": block["end_time"], "timeZone": timezone},
    }
    return service.events().insert(
        calendarId=calendar_id or "primary",
        body=event
    ).execute()
```

---

## 21. Supabase Storage Design

For MVP, use text ingestion first because Copilot REST actions are easiest with JSON.

For actual file uploads, use one of these patterns:

### Option A: Backend multipart upload endpoint

```http
POST /documents/upload
Content-Type: multipart/form-data
```

### Option B: Signed upload URL

```http
POST /documents/upload-url
```

### Option C: Pasted text through Copilot

```http
POST /copilot/documents/ingest-text
```

### Recommended for first demo

Use Option C first. Then add Option A for a simple upload web page.

---

## 22. Dockerfile for Cloud Run

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
```

Test locally with Docker:

```bash
docker build -t academic-context-api .
docker run --env-file .env -p 8080:8080 academic-context-api
```

---

## 23. Deploy to Google Cloud Run

```bash
gcloud auth login
gcloud config set project YOUR_GCP_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com

gcloud run deploy academic-context-api \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --set-env-vars APP_ENV=production
```

For production, put secrets in Google Secret Manager.

---

## 24. OpenAPI / Swagger for Copilot Studio

FastAPI automatically exposes `/openapi.json`. Copilot Studio works best with Swagger 2.0.

```bash
npm install -g api-spec-converter
curl http://localhost:8000/openapi.json -o openapi.json
api-spec-converter --from=openapi_3 --to=swagger_2 --syntax=json openapi.json > swagger-v2.json
```

Before uploading, check:

```json
{
  "swagger": "2.0",
  "host": "academic-context-api-xxxxx.a.run.app",
  "basePath": "/",
  "schemes": ["https"]
}
```

Add API key security:

```json
"securityDefinitions": {
  "api_key": {
    "type": "apiKey",
    "name": "x-copilot-api-key",
    "in": "header"
  }
},
"security": [{"api_key": []}]
```

Expose these actions to Copilot Studio:

```text
upsertStudentProfile
ingestAcademicText
extractAcademicItems
confirmAcademicItems
getPlanningContext
saveStudyPlan
updateStudyPlan
updateStudyBlockStatus
createCalendarStudyEvents
syncCalendarBusyBlocks
```

---

## 25. Connect API to Microsoft Copilot Studio

1. Open Copilot Studio.
2. Open the Academic Planning Agent.
3. Go to Tools / Actions.
4. Add action → REST API (or import a custom connector).
5. Upload `swagger-v2.json`.
6. Configure API key header: `x-copilot-api-key`.
7. Select actions to expose.
8. Add clear action descriptions.
9. Publish and test.

### Tool descriptions for Copilot

```text
upsertStudentProfile:
Use when the student provides or updates name, email, timezone, study preferences, or availability.

ingestAcademicText:
Use when the student pastes syllabus text, assignment instructions, or deadline information.

extractAcademicItems:
Use after academic text has been stored. Extracts factual items (assignments, exams, quizzes, readings) with due dates, weights, and confidence scores. Does NOT score priority — that is your job.

confirmAcademicItems:
Use after asking the student to confirm low-confidence items. Updates the saved items.

getPlanningContext:
Use whenever you need to think about a study week. Returns the student profile, deadlines, busy calendar blocks, preferences, existing study blocks, document context, and data warnings. You then reason over this to propose a plan.

saveStudyPlan:
Use after you have proposed a plan to the student and they have approved (or to checkpoint a draft). You send the blocks you composed. The backend does NOT generate the plan.

updateStudyPlan:
Use when revising a saved plan (e.g., student says they are busy on a specific day, or missed a block).

updateStudyBlockStatus:
Use when the student says they completed or missed a specific study block.

createCalendarStudyEvents:
Use ONLY after the student approves the plan and explicitly agrees to add blocks to the selected calendar provider.

syncCalendarBusyBlocks:
Use to refresh selected provider busy data before calling getPlanningContext if availability may have changed.
```

---

## 26. Copilot Studio Agent Instruction Draft

Use this as the base instruction in Copilot Studio:

```text
You are an Academic Planning Assistant for university students. You are the brain of this product.

Your role is to help students organize academic requirements, understand deadlines, plan study blocks, detect workload conflicts, and maintain realistic study schedules.

You support students, but you do not replace their academic responsibility. Do not complete assignments, write final submissions, take exams, or produce work that the student can submit as their own. You may help break down tasks, explain requirements, suggest study strategies, summarize course materials, and propose study plans.

You have a backend "Academic Context API" with tools to:
- save the student profile
- ingest academic text
- extract factual academic items from documents
- confirm corrected academic items
- get planning context (deadlines, busy calendar blocks, preferences, document context, warnings)
- save a study plan you have composed
- update a saved study plan
- update a study block's status
- create calendar provider events from approved plans
- sync calendar provider busy blocks

The backend serves facts and persists your decisions. It does NOT decide priorities, detect conflicts, or write the plan. You do that.

When a student asks for planning help:

1. Identify the student's goal.
2. Check whether academic inputs are available. If something is missing, ask a clear follow-up question.
3. Use ingestAcademicText and extractAcademicItems to capture academic facts.
4. If any extracted items have low confidence or need_confirmation = true, ask the student to confirm and call confirmAcademicItems.
5. Call getPlanningContext for the planning window.
6. Read the context yourself: deadlines, weights, estimated hours, busy blocks, preferred study times, data_warnings.
7. Reason about prioritization: what is heaviest, what is due soonest, where are the conflicts, how should the week be shaped. Explain this to the student in plain language.
8. Propose a concrete plan (specific study blocks with times) and ask for approval.
9. Once approved, call saveStudyPlan with status="approved" and the blocks you composed.
10. Ask the student if you should add the blocks to the selected calendar provider. If yes, call createCalendarStudyEvents.
11. If the student later says their availability changed or they missed a block, compose the revised blocks yourself and call updateStudyPlan. For single completed/missed blocks, call updateStudyBlockStatus.

Always prioritize accuracy, clarity, and student wellbeing. If extracted information is uncertain, confirm before using it. Never invent due dates.
```

---

## 27. Local API Testing

### Health check

```bash
curl http://localhost:8000/health
```

### Upsert student

```bash
curl -X POST http://localhost:8000/copilot/students/upsert \
  -H "Content-Type: application/json" \
  -H "x-copilot-api-key: YOUR_LOCAL_KEY" \
  -d '{
    "copilot_user_id": "demo-user-1",
    "name": "Demo Student",
    "email": "demo@example.com",
    "timezone": "Asia/Manila",
    "preferred_study_style": "short focused blocks",
    "preferred_study_times": [{"day": "weekday", "start": "19:00", "end": "22:00"}]
  }'
```

### Get planning context

```bash
curl "http://localhost:8000/copilot/planning-context?copilot_user_id=demo-user-1&start_date=2026-06-10&end_date=2026-06-17" \
  -H "x-copilot-api-key: YOUR_LOCAL_KEY"
```

### Save a Copilot-composed plan

```bash
curl -X POST http://localhost:8000/copilot/study-plans/save \
  -H "Content-Type: application/json" \
  -H "x-copilot-api-key: YOUR_LOCAL_KEY" \
  -d '{
    "copilot_user_id": "demo-user-1",
    "start_date": "2026-06-10",
    "end_date": "2026-06-17",
    "status": "approved",
    "summary": "Project first, quiz review Thursday.",
    "reasoning": "Project is heavier and due first.",
    "blocks": [
      {
        "title": "Work on CS101 Final Project Proposal",
        "start_time": "2026-06-11T19:00:00+08:00",
        "end_time": "2026-06-11T21:00:00+08:00"
      }
    ]
  }'
```

---

## 28. Implementation Order

### Step 1: API foundation

```text
- FastAPI app
- Health endpoint
- Config
- API key security
- Supabase client
```

### Step 2: Supabase schema

```text
- Run SQL migration (see 3-db_tables.md)
- Create academic-documents storage bucket
- Enable vector extension
```

### Step 3: Student and document endpoints

```text
- Upsert student
- Create/find course
- Ingest academic text
- Store document record
```

### Step 4: OpenAI extraction (utility only)

```text
- Structured extraction schema (facts only, no priority)
- Extract academic items
- Save to academic_items table
- Return items + clarifying_questions to Copilot
```

### Step 5: Planning context endpoint

```text
- Assemble student + courses + items + busy_blocks + study_blocks + warnings
- No scoring, no conflict detection — just facts
```

### Step 6: Save / update study plan endpoints

```text
- Persist Copilot-composed plans and blocks
- Status flow: draft → approved
```

### Step 7: Calendar provider OAuth

```text
- OAuth start endpoint
- OAuth callback endpoint
- Token encryption
- Calendar connection storage
```

### Step 8: calendar provider event creation

```text
- Create events only from approved plans
- Save provider event id on study_blocks (`google_calendar_event_id` legacy field name or `calendar_event_id` if migrated)
- Optional: sync-busy endpoint
```

### Step 9: Copilot Studio connection

```text
- Export OpenAPI
- Convert to Swagger 2.0
- Upload to Copilot Studio
- Add action descriptions (emphasizing Copilot is the brain)
- Test agent flow end-to-end
```

---

## 29. Demo Script for the Challenge

```text
Student:
Help me plan my week.

Copilot:
Sure. Please paste your syllabus, assignment details, or deadlines.

Student:
Final Project Proposal is due June 15 at 11:59 PM and is worth 20%. Quiz 2 is due June 12. Midterm Exam is on June 18.

Copilot calls:
- ingestAcademicText
- extractAcademicItems
(asks for confirmation of any low-confidence items if needed)
- getPlanningContext (start=June 10, end=June 18)

Copilot reads the context, reasons about it, and says:
"I found 3 academic items in that window. The project (20%, ~8h) and quiz are close together, so I'd suggest starting the project on Wednesday evening, taking Thursday for quiz review, and keeping June 17 for exam review. Want me to lay it out?"

Student:
Yes.

Copilot proposes specific blocks with times, explains its reasoning, and asks for approval.

Student:
Approved. Add to my calendar.

Copilot calls:
- saveStudyPlan (status="approved", with the blocks Copilot composed)
- createCalendarStudyEvents

Copilot:
Done. I added your study blocks to the selected calendar provider.

Student:
I'm busy Wednesday night.

Copilot composes a revision, then calls:
- updateStudyPlan (with the moved blocks)
- (optionally re-creates calendar events for the moved blocks)

Copilot:
No problem. I moved Wednesday night's block to Thursday and kept your exam review protected.
```

---

## 30. Non-Negotiable Product Rules

```text
1. Copilot Studio is the brain. The backend serves facts and persists decisions.
2. Never create or update calendar events without explicit student approval.
3. Never invent due dates. If unclear, set due_date null and ask via clarifying_questions.
4. Always store confidence score for extracted academic items.
5. The backend does NOT score priority, detect conflicts, or write plan narratives.
6. OpenAI in the backend is an extraction/embedding utility only.
7. Store uploaded documents privately.
8. Do not expose Supabase service role key, OpenAI key, or Google client secret.
9. Do not write final assignment submissions for the student.
10. Refuse /calendar/create-events for non-approved plans.
```

---

## 31. Next Development Task

Start coding in this order:

```text
1. FastAPI app + /health
2. /copilot/students/upsert
3. /copilot/documents/ingest-text
4. Supabase schema (see 3-db_tables.md)
5. OpenAI extraction utility + /copilot/academic-items/extract
6. /copilot/academic-items/confirm
7. /copilot/planning-context
8. /copilot/study-plans/save and /copilot/study-plans/update
9. Calendar provider OAuth + /copilot/calendar/create-events
```

Then connect to Copilot Studio.
