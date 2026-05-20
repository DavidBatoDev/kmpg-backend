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
    status: str = "draft"
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
