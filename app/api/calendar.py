from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

from app.services import calendar_service

router = APIRouter()


@router.get("/oauth/start")
def oauth_start(
    copilot_user_id: str,
    provider: str = Query(default="google"),
    redirect_after_connect: str | None = Query(default=None),
):
    url = calendar_service.build_oauth_start_url(copilot_user_id, provider, redirect_after_connect)
    return RedirectResponse(url=url, status_code=302)


@router.get("/oauth/callback")
def oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    return calendar_service.handle_oauth_callback(code, state, error, error_description)
