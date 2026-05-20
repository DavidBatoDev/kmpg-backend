from datetime import date

from fastapi import HTTPException, status


def get_context(copilot_user_id: str, start_date: date, end_date: date) -> dict:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Planning context assembly not implemented yet.",
    )
