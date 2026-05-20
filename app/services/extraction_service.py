from fastapi import HTTPException, status

from app.schemas.copilot import (
    ConfirmAcademicItemsRequest,
    ExtractAcademicItemsRequest,
)


def extract_and_save_items(payload: ExtractAcademicItemsRequest) -> dict:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="OpenAI extraction not implemented yet.",
    )


def confirm_items(payload: ConfirmAcademicItemsRequest) -> dict:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Academic item confirmation not implemented yet.",
    )
