from fastapi import HTTPException, status

from app.schemas.copilot import CreateCalendarEventsRequest, SyncBusyRequest


def create_study_events(payload: CreateCalendarEventsRequest) -> dict:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Google Calendar event creation not implemented yet.",
    )


def sync_busy_blocks(payload: SyncBusyRequest) -> dict:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Calendar busy sync not implemented yet.",
    )
