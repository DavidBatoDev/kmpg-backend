from fastapi import HTTPException, status

from app.db.supabase import get_supabase
from app.schemas.copilot import (
    SaveStudyPlanRequest,
    StudyBlockStatusRequest,
    UpdateStudyPlanRequest,
)
from app.services import student_service


def save_plan(payload: SaveStudyPlanRequest) -> dict:
    supabase = get_supabase()
    student = student_service.get_student_by_copilot_id(payload.copilot_user_id)
    student_id = student["id"]

    if payload.status not in {"draft", "approved"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="status must be draft or approved.")

    plan_result = (
        supabase.table("study_plans")
        .insert(
            {
                "student_id": student_id,
                "status": payload.status,
                "start_date": payload.start_date.isoformat(),
                "end_date": payload.end_date.isoformat(),
                "goal": payload.goal,
                "summary": payload.summary,
                "reasoning": payload.reasoning,
            }
        )
        .execute()
    )
    if not plan_result.data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save study plan.")
    plan_id = plan_result.data[0]["id"]

    blocks_payload = []
    for b in payload.blocks:
        blocks_payload.append(
            {
                "study_plan_id": plan_id,
                "student_id": student_id,
                "academic_item_id": b.academic_item_id,
                "title": b.title,
                "description": b.description,
                "start_time": b.start_time.isoformat(),
                "end_time": b.end_time.isoformat(),
                "status": "approved" if payload.status == "approved" else "proposed",
            }
        )

    block_ids: list[str] = []
    if blocks_payload:
        block_result = supabase.table("study_blocks").insert(blocks_payload).execute()
        for row in block_result.data or []:
            block_ids.append(row["id"])

    return {"study_plan_id": plan_id, "block_ids": block_ids, "message": "Study plan saved."}


def update_plan(payload: UpdateStudyPlanRequest) -> dict:
    supabase = get_supabase()
    student = student_service.get_student_by_copilot_id(payload.copilot_user_id)
    student_id = student["id"]

    existing = (
        supabase.table("study_plans")
        .select("id,status")
        .eq("id", payload.study_plan_id)
        .eq("student_id", student_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study plan not found.")

    plan_update = {}
    if payload.status is not None:
        plan_update["status"] = payload.status
    if payload.summary is not None:
        plan_update["summary"] = payload.summary
    if payload.reasoning is not None:
        plan_update["reasoning"] = payload.reasoning
    if plan_update:
        supabase.table("study_plans").update(plan_update).eq("id", payload.study_plan_id).eq("student_id", student_id).execute()

    if payload.blocks_replace is not None:
        supabase.table("study_blocks").delete().eq("study_plan_id", payload.study_plan_id).eq("student_id", student_id).execute()
        new_blocks = []
        for b in payload.blocks_replace:
            new_blocks.append(
                {
                    "study_plan_id": payload.study_plan_id,
                    "student_id": student_id,
                    "academic_item_id": b.academic_item_id,
                    "title": b.title,
                    "description": b.description,
                    "start_time": b.start_time.isoformat(),
                    "end_time": b.end_time.isoformat(),
                    "status": "approved" if payload.status == "approved" else "proposed",
                }
            )
        if new_blocks:
            supabase.table("study_blocks").insert(new_blocks).execute()

    return {"study_plan_id": payload.study_plan_id, "message": "Study plan updated."}


def update_block_status(payload: StudyBlockStatusRequest) -> dict:
    supabase = get_supabase()
    student = student_service.get_student_by_copilot_id(payload.copilot_user_id)
    student_id = student["id"]

    allowed = {"proposed", "approved", "scheduled", "completed", "missed", "cancelled", "rescheduled"}
    if payload.status not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid study block status.")

    result = (
        supabase.table("study_blocks")
        .update({"status": payload.status})
        .eq("id", payload.study_block_id)
        .eq("student_id", student_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study block not found.")

    return {"study_block_id": payload.study_block_id, "status": payload.status}
