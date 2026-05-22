import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status

from app.core.config import settings
from app.db.supabase import get_supabase
from app.schemas.copilot import ConfirmAcademicItemsRequest, ExtractAcademicItemsRequest
from app.services import student_service

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional runtime import
    OpenAI = None


TYPE_OPTIONS = ("assignment", "exam", "quiz", "project", "reading", "presentation", "lab", "other")


def _guess_type(title: str) -> str:
    lower = title.lower()
    for t in TYPE_OPTIONS:
        if t in lower:
            return t
    return "other"


def _parse_due_date(text: str, timezone: str) -> tuple[str | None, float, bool]:
    # Supports "June 15", "Jun 15", optionally with year/time.
    m = re.search(
        r"\b(?P<month>jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
        r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+"
        r"(?P<day>\d{1,2})(?:,?\s*(?P<year>\d{4}))?",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None, 0.45, True

    month = m.group("month")
    day = int(m.group("day"))
    year = int(m.group("year")) if m.group("year") else datetime.now(ZoneInfo(timezone)).year
    dt = datetime.strptime(f"{month} {day} {year}", "%b %d %Y") if len(month) <= 3 else datetime.strptime(
        f"{month} {day} {year}", "%B %d %Y"
    )

    # Time detection
    has_time = bool(re.search(r"\b\d{1,2}(:\d{2})?\s?(am|pm)\b|23:59|11:59", text, re.IGNORECASE))
    if has_time:
        tm = re.search(r"(\d{1,2})(?::(\d{2}))?\s?(am|pm)", text, re.IGNORECASE)
        if tm:
            hr = int(tm.group(1))
            minute = int(tm.group(2) or 0)
            ampm = tm.group(3).lower()
            if ampm == "pm" and hr != 12:
                hr += 12
            if ampm == "am" and hr == 12:
                hr = 0
            dt = dt.replace(hour=hr, minute=minute)
        elif "23:59" in text or "11:59" in text:
            dt = dt.replace(hour=23, minute=59)
    else:
        dt = dt.replace(hour=23, minute=59)

    due = dt.replace(tzinfo=ZoneInfo(timezone)).isoformat()
    confidence = 0.88 if has_time else 0.72
    needs_confirmation = not has_time
    return due, confidence, needs_confirmation


def _extract_fallback(source_text: str, timezone: str) -> dict:
    lines = [l.strip() for l in re.split(r"[\n;]+", source_text) if l.strip()]
    items = []
    clarifying_questions: list[str] = []

    for line in lines:
        if not re.search(r"due|exam|quiz|project|assignment|reading|presentation|lab", line, re.IGNORECASE):
            continue
        title = line[:120]
        due_date, due_conf, needs_confirmation = _parse_due_date(line, timezone)
        weight_match = re.search(r"(\d{1,3})\s*%", line)
        weight = float(weight_match.group(1)) if weight_match else None
        confidence = min(due_conf, 0.85 if weight is not None else 0.8)
        if due_date is None:
            clarifying_questions.append(f"What is the exact due date for '{title}'?")
        elif needs_confirmation:
            clarifying_questions.append(f"Can you confirm the due time for '{title}'?")

        items.append(
            {
                "type": _guess_type(title),
                "title": title,
                "description": line,
                "due_date": due_date,
                "due_date_confidence": due_conf,
                "weight": weight,
                "estimated_hours": None,
                "confidence_score": confidence,
                "needs_confirmation": needs_confirmation,
                "source_quote": line,
                "status": "pending",
            }
        )

    return {"items": items, "clarifying_questions": clarifying_questions}


def _extract_with_openai(source_text: str, timezone: str) -> dict:
    if not settings.openai_api_key or OpenAI is None:
        return _extract_fallback(source_text, timezone)

    client = OpenAI(api_key=settings.openai_api_key)
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "academic_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "type": {"type": "string", "enum": list(TYPE_OPTIONS)},
                        "title": {"type": "string"},
                        "description": {"type": ["string", "null"]},
                        "due_date": {"type": ["string", "null"]},
                        "weight": {"type": ["number", "null"]},
                        "estimated_hours": {"type": ["number", "null"]},
                        "confidence_score": {"type": "number"},
                        "source_quote": {"type": ["string", "null"]},
                    },
                    "required": [
                        "type",
                        "title",
                        "description",
                        "due_date",
                        "weight",
                        "estimated_hours",
                        "confidence_score",
                        "source_quote",
                    ],
                },
            },
            "clarifying_questions": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["academic_items", "clarifying_questions"],
    }

    try:
        response = client.responses.create(
            model=settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Extract factual academic requirements only. Do not prioritize or plan. "
                        "If date is ambiguous set due_date null and add clarifying question. "
                        f"Timezone is {timezone}."
                    ),
                },
                {"role": "user", "content": source_text},
            ],
            text={"format": {"type": "json_schema", "name": "academic_extraction", "schema": schema, "strict": True}},
        )
        parsed = json.loads(response.output_text)
        items = []
        for item in parsed.get("academic_items", []):
            due = item.get("due_date")
            needs_confirmation = item.get("confidence_score", 0) < 0.7 or due is None
            items.append(
                {
                    "type": item["type"],
                    "title": item["title"],
                    "description": item.get("description"),
                    "due_date": due,
                    "due_date_confidence": item.get("confidence_score", 0.5),
                    "weight": item.get("weight"),
                    "estimated_hours": item.get("estimated_hours"),
                    "confidence_score": item.get("confidence_score", 0.5),
                    "needs_confirmation": needs_confirmation,
                    "source_quote": item.get("source_quote"),
                    "status": "pending",
                }
            )
        return {"items": items, "clarifying_questions": parsed.get("clarifying_questions", [])}
    except Exception:
        return _extract_fallback(source_text, timezone)


def extract_and_save_items(payload: ExtractAcademicItemsRequest) -> dict:
    supabase = get_supabase()
    student = student_service.get_student_by_copilot_id(payload.copilot_user_id)

    doc_result = (
        supabase.table("documents")
        .select("id, student_id, course_id, source_text")
        .eq("id", payload.document_id)
        .eq("student_id", student["id"])
        .limit(1)
        .execute()
    )
    if not doc_result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found for this student.")
    doc = doc_result.data[0]
    source_text = doc.get("source_text") or ""
    if len(source_text.strip()) < 10:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document has no extractable source_text.")

    extracted = _extract_with_openai(source_text, student.get("timezone", "Asia/Manila"))
    items_payload = []
    for item in extracted["items"]:
        items_payload.append(
            {
                **item,
                "student_id": student["id"],
                "course_id": doc.get("course_id"),
                "document_id": doc["id"],
            }
        )

    created_items = []
    if items_payload:
        insert_result = supabase.table("academic_items").insert(items_payload).execute()
        created_items = insert_result.data or []

    supabase.table("documents").update({"extraction_status": "completed"}).eq("id", doc["id"]).execute()

    response_items = []
    for item in created_items:
        response_items.append(
            {
                "id": item["id"],
                "type": item["type"],
                "title": item["title"],
                "due_date": item["due_date"],
                "weight": item["weight"],
                "estimated_hours": item["estimated_hours"],
                "confidence_score": item["confidence_score"],
                "needs_confirmation": item["needs_confirmation"],
                "source_quote": item["source_quote"],
            }
        )

    message = f"I found {len(response_items)} academic item{'s' if len(response_items) != 1 else ''}."
    return {
        "items": response_items,
        "clarifying_questions": extracted.get("clarifying_questions", []),
        "message": message,
    }


def confirm_items(payload: ConfirmAcademicItemsRequest) -> dict:
    supabase = get_supabase()
    student = student_service.get_student_by_copilot_id(payload.copilot_user_id)

    updated = 0
    for item in payload.items:
        row_result = (
            supabase.table("academic_items")
            .select("id")
            .eq("id", item.id)
            .eq("student_id", student["id"])
            .limit(1)
            .execute()
        )
        if not row_result.data:
            continue

        if item.confirmed:
            update_row = {
                "status": "confirmed",
                "needs_confirmation": False,
                "metadata": {"confirmation_source": "student"},
            }
            if item.due_date is not None:
                update_row["due_date"] = item.due_date.isoformat()
            if item.weight is not None:
                update_row["weight"] = item.weight
            if item.estimated_hours is not None:
                update_row["estimated_hours"] = item.estimated_hours
        else:
            update_row = {
                "status": "cancelled",
                "needs_confirmation": False,
                "metadata": {"cancelled_reason": item.cancelled_reason or "not_confirmed"},
            }

        supabase.table("academic_items").update(update_row).eq("id", item.id).eq("student_id", student["id"]).execute()
        updated += 1

    return {"updated": updated, "message": "Academic items updated."}
