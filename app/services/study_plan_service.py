from fastapi import HTTPException, status

from app.schemas.copilot import (
    SaveStudyPlanRequest,
    StudyBlockStatusRequest,
    UpdateStudyPlanRequest,
)


def save_plan(payload: SaveStudyPlanRequest) -> dict:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Study plan save not implemented yet.",
    )


def update_plan(payload: UpdateStudyPlanRequest) -> dict:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Study plan update not implemented yet.",
    )


def update_block_status(payload: StudyBlockStatusRequest) -> dict:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Study block status update not implemented yet.",
    )
