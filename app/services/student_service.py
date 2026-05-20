from fastapi import HTTPException, status

from app.db.supabase import get_supabase
from app.schemas.copilot import StudentUpsertRequest


def get_student_by_copilot_id(copilot_user_id: str) -> dict:
    supabase = get_supabase()
    result = (
        supabase.table("students")
        .select("*")
        .eq("copilot_user_id", copilot_user_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student not found for copilot_user_id={copilot_user_id}",
        )
    return result.data[0]


def upsert_student(payload: StudentUpsertRequest) -> dict:
    supabase = get_supabase()
    row = {
        "copilot_user_id": payload.copilot_user_id,
        "name": payload.name,
        "email": payload.email,
        "timezone": payload.timezone,
        "preferred_study_style": payload.preferred_study_style,
        "preferred_study_times": [t.model_dump() for t in payload.preferred_study_times],
    }
    result = (
        supabase.table("students")
        .upsert(row, on_conflict="copilot_user_id")
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upsert student",
        )
    student = result.data[0]
    return {
        "student_id": student["id"],
        "message": "Student profile saved.",
    }
