from datetime import date

from fastapi import HTTPException, status

from app.db.supabase import get_supabase
from app.services import student_service


def get_context(copilot_user_id: str, start_date: date, end_date: date) -> dict:
    if end_date < start_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_date must be on/after start_date.")

    supabase = get_supabase()
    student = student_service.get_student_by_copilot_id(copilot_user_id)
    student_id = student["id"]
    start_iso = f"{start_date.isoformat()}T00:00:00+00:00"
    end_iso = f"{end_date.isoformat()}T23:59:59+00:00"

    courses = supabase.table("courses").select("*").eq("student_id", student_id).execute().data or []

    items = (
        supabase.table("academic_items")
        .select("*")
        .eq("student_id", student_id)
        .in_("status", ["pending", "confirmed", "in_progress"])
        .order("due_date", desc=False)
        .execute()
        .data
        or []
    )
    # Filter in python for compatibility with null due dates
    filtered_items = []
    for item in items:
        due = item.get("due_date")
        if due is None:
            filtered_items.append(item)
            continue
        if start_iso <= due <= end_iso:
            filtered_items.append(item)

    busy_blocks = (
        supabase.table("calendar_busy_blocks")
        .select("start_time,end_time,title,is_all_day,external_event_id,provider")
        .eq("student_id", student_id)
        .gte("end_time", start_iso)
        .lte("start_time", end_iso)
        .order("start_time", desc=False)
        .execute()
        .data
        or []
    )

    study_blocks = (
        supabase.table("study_blocks")
        .select("id,title,start_time,end_time,status,academic_item_id,study_plan_id,google_calendar_event_id,calendar_html_link")
        .eq("student_id", student_id)
        .gte("end_time", start_iso)
        .lte("start_time", end_iso)
        .order("start_time", desc=False)
        .execute()
        .data
        or []
    )

    warnings = []
    for item in filtered_items:
        if item.get("confidence_score", 0) < 0.7 or item.get("needs_confirmation") or item.get("due_date") is None:
            warnings.append(
                {
                    "type": "low_confidence_due_date" if item.get("due_date") else "missing_due_date",
                    "academic_item_id": item["id"],
                    "message": f"{item.get('title', 'Item')} may need confirmation.",
                }
            )

    connections = supabase.table("calendar_connections").select("provider,connection_status").eq("student_id", student_id).execute().data or []
    active_connections = [c for c in connections if c.get("connection_status") == "active"]
    if not active_connections:
        warnings.append(
            {
                "type": "missing_calendar_connection",
                "provider_hint": "google",
                "message": "Selected calendar provider is not connected, so busy blocks may be incomplete.",
            }
        )

    if not student.get("preferred_study_times"):
        warnings.append(
            {
                "type": "missing_preferred_study_times",
                "message": "Preferred study times are not set.",
            }
        )

    return {
        "student": {
            "name": student.get("name"),
            "timezone": student.get("timezone"),
            "preferred_study_style": student.get("preferred_study_style"),
            "preferred_study_times": student.get("preferred_study_times", []),
        },
        "courses": courses,
        "academic_items": filtered_items,
        "calendar_busy_blocks": busy_blocks,
        "existing_study_blocks": study_blocks,
        "document_context": [],
        "data_warnings": warnings,
    }
