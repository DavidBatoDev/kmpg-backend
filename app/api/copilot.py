from datetime import date

from fastapi import APIRouter, Depends

from app.core.security import verify_copilot_api_key
from app.schemas.copilot import (
    ConfirmAcademicItemsRequest,
    CreateCalendarEventsRequest,
    ExtractAcademicItemsRequest,
    IngestTextRequest,
    SaveStudyPlanRequest,
    StudentUpsertRequest,
    StudyBlockStatusRequest,
    SyncBusyRequest,
    UpdateStudyPlanRequest,
)
from app.services import (
    calendar_service,
    document_service,
    extraction_service,
    planning_context_service,
    student_service,
    study_plan_service,
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
def planning_context(copilot_user_id: str, start_date: date, end_date: date):
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
