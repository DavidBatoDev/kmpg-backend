from fastapi import APIRouter, Depends

from app.core.security import verify_copilot_api_key

router = APIRouter()


@router.get("/oauth/start")
def oauth_start(copilot_user_id: str):
    return {
        "message": "Not implemented.",
        "copilot_user_id": copilot_user_id,
    }


@router.get("/oauth/callback")
def oauth_callback(code: str | None = None, state: str | None = None):
    return {
        "message": "Not implemented.",
        "code_received": code is not None,
        "state": state,
    }
