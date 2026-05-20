from fastapi import HTTPException, status

from app.db.supabase import get_supabase
from app.schemas.copilot import IngestTextRequest
from app.services import student_service


def _get_or_create_course(supabase, student_id: str, payload: IngestTextRequest) -> str | None:
    if not payload.course_name:
        return None
    existing = (
        supabase.table("courses")
        .select("id")
        .eq("student_id", student_id)
        .eq("course_name", payload.course_name)
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]["id"]
    insert = (
        supabase.table("courses")
        .insert(
            {
                "student_id": student_id,
                "course_code": payload.course_code,
                "course_name": payload.course_name,
            }
        )
        .execute()
    )
    if not insert.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create course",
        )
    return insert.data[0]["id"]


def ingest_text(payload: IngestTextRequest) -> dict:
    supabase = get_supabase()
    student = student_service.get_student_by_copilot_id(payload.copilot_user_id)
    course_id = _get_or_create_course(supabase, student["id"], payload)
    doc = (
        supabase.table("documents")
        .insert(
            {
                "student_id": student["id"],
                "course_id": course_id,
                "file_name": payload.document_name,
                "source_text": payload.text,
                "processing_status": "completed",
                "extraction_status": "not_started",
            }
        )
        .execute()
    )
    if not doc.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store document",
        )
    document = doc.data[0]
    return {
        "document_id": document["id"],
        "course_id": course_id,
        "message": "Document text stored and ready for extraction.",
    }
