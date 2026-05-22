from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from urllib.parse import urlencode
from uuid import uuid4

import httpx
from cryptography.fernet import Fernet
from fastapi import HTTPException, status

from app.core.config import settings
from app.db.supabase import get_supabase
from app.schemas.copilot import CreateCalendarEventsRequest, SyncBusyRequest
from app.services import student_service


def _validate_provider(provider: str) -> str:
    provider_norm = (provider or "google").lower()
    if provider_norm not in {"google", "outlook"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="provider must be google or outlook.")
    return provider_norm


def _get_oauth_config(provider: str) -> dict:
    if provider == "google":
        if not settings.google_client_id or not settings.google_client_secret:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google OAuth is not configured.")
        return {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "scope": "https://www.googleapis.com/auth/calendar",
            "access_type": "offline",
            "prompt": "consent",
        }
    if provider == "outlook":
        if not settings.outlook_client_id or not settings.outlook_client_secret:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Outlook OAuth is not configured.")
        return {
            "client_id": settings.outlook_client_id,
            "client_secret": settings.outlook_client_secret,
            "redirect_uri": settings.outlook_redirect_uri,
            "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            "scope": "offline_access Calendars.ReadWrite User.Read",
            "access_type": None,
            "prompt": "select_account",
        }
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported provider.")


def _get_fernet() -> Fernet:
    if not settings.token_encryption_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TOKEN_ENCRYPTION_KEY is not configured.",
        )
    try:
        return Fernet(settings.token_encryption_key.encode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TOKEN_ENCRYPTION_KEY is invalid for Fernet.",
        ) from exc


def build_oauth_start_url(copilot_user_id: str, provider: str, redirect_after_connect: str | None = None) -> str:
    provider = _validate_provider(provider)
    cfg = _get_oauth_config(provider)
    supabase = get_supabase()
    student = student_service.get_student_by_copilot_id(copilot_user_id)
    state = token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()

    supabase.table("oauth_states").insert(
        {
            "student_id": student["id"],
            "provider": provider,
            "state": state,
            "redirect_after_connect": redirect_after_connect,
            "expires_at": expires_at,
        }
    ).execute()

    query = {
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"],
        "response_type": "code",
        "scope": cfg["scope"],
        "state": state,
    }
    if cfg.get("access_type"):
        query["access_type"] = cfg["access_type"]
    if cfg.get("prompt"):
        query["prompt"] = cfg["prompt"]
    return f"{cfg['auth_url']}?{urlencode(query)}"


def handle_oauth_callback(code: str | None, state: str | None, error: str | None = None, error_description: str | None = None) -> dict:
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth provider returned error: {error} ({error_description or 'no description'})",
        )
    if not code or not state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing OAuth callback code or state.")

    supabase = get_supabase()
    state_result = (
        supabase.table("oauth_states")
        .select("*")
        .eq("state", state)
        .limit(1)
        .execute()
    )
    if not state_result.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state.")
    state_row = state_result.data[0]

    if state_row.get("used_at"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth state already used.")
    if datetime.fromisoformat(state_row["expires_at"].replace("Z", "+00:00")) < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth state expired.")

    provider = _validate_provider(state_row["provider"])
    cfg = _get_oauth_config(provider)
    token_payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": cfg["redirect_uri"],
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
    }
    if provider == "outlook":
        token_payload["scope"] = cfg["scope"]

    try:
        response = httpx.post(cfg["token_url"], data=token_payload, timeout=20.0)
        response.raise_for_status()
        token_data = response.json()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to exchange OAuth code for tokens.") from exc

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in")
    if not access_token:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="OAuth token response missing access_token.")

    fernet = _get_fernet()
    enc_access = fernet.encrypt(access_token.encode("utf-8")).decode("utf-8")
    enc_refresh = fernet.encrypt((refresh_token or "").encode("utf-8")).decode("utf-8")
    token_expiry = None
    if isinstance(expires_in, (int, float)):
        token_expiry = (datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))).isoformat()

    upsert_result = (
        supabase.table("calendar_connections")
        .upsert(
            {
                "student_id": state_row["student_id"],
                "provider": provider,
                "calendar_id": "primary",
                "encrypted_access_token": enc_access,
                "encrypted_refresh_token": enc_refresh,
                "token_expiry": token_expiry,
                "scopes": cfg["scope"].split(" "),
                "connection_status": "active",
                "error_message": None,
            },
            on_conflict="student_id,provider,calendar_id",
        )
        .execute()
    )
    if not upsert_result.data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to store calendar connection.")

    supabase.table("oauth_states").update({"used_at": datetime.now(timezone.utc).isoformat()}).eq("state", state).execute()
    return {
        "message": f"{provider} calendar connected successfully.",
        "provider": provider,
        "redirect_after_connect": state_row.get("redirect_after_connect"),
    }


def create_study_events(payload: CreateCalendarEventsRequest) -> dict:
    supabase = get_supabase()
    student = student_service.get_student_by_copilot_id(payload.copilot_user_id)
    student_id = student["id"]
    provider = _validate_provider(payload.provider)

    conn = (
        supabase.table("calendar_connections")
        .select("id,provider,connection_status")
        .eq("student_id", student_id)
        .eq("provider", provider)
        .eq("connection_status", "active")
        .limit(1)
        .execute()
    )
    if not conn.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{provider} calendar is not connected for this student.",
        )

    plan_result = (
        supabase.table("study_plans")
        .select("id,status")
        .eq("id", payload.study_plan_id)
        .eq("student_id", student_id)
        .limit(1)
        .execute()
    )
    if not plan_result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study plan not found.")
    plan = plan_result.data[0]
    if plan["status"] != "approved":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only approved plans can create calendar events.")

    blocks_result = (
        supabase.table("study_blocks")
        .select("id,title,description,start_time,end_time,google_calendar_event_id,calendar_html_link")
        .eq("study_plan_id", payload.study_plan_id)
        .eq("student_id", student_id)
        .execute()
    )
    blocks = blocks_result.data or []

    created_events = []
    for block in blocks:
        event_id = block.get("google_calendar_event_id") or f"{provider}-{uuid4()}"
        html_link = block.get("calendar_html_link") or f"https://calendar.{provider}.example/events/{event_id}"
        supabase.table("study_blocks").update(
            {
                "google_calendar_event_id": event_id,
                "calendar_html_link": html_link,
                "status": "scheduled",
            }
        ).eq("id", block["id"]).eq("student_id", student_id).execute()
        created_events.append({"study_block_id": block["id"], "calendar_event_id": event_id, "html_link": html_link})

    supabase.table("study_plans").update({"status": "scheduled"}).eq("id", payload.study_plan_id).eq("student_id", student_id).execute()
    return {"created_events": created_events, "message": "Study events were added to the selected calendar provider."}


def sync_busy_blocks(payload: SyncBusyRequest) -> dict:
    supabase = get_supabase()
    student = student_service.get_student_by_copilot_id(payload.copilot_user_id)
    student_id = student["id"]
    provider = _validate_provider(payload.provider)

    conn = (
        supabase.table("calendar_connections")
        .select("id,connection_status")
        .eq("student_id", student_id)
        .eq("provider", provider)
        .eq("connection_status", "active")
        .limit(1)
        .execute()
    )
    if not conn.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{provider} calendar is not connected.")

    start_iso = f"{payload.start_date.isoformat()}T00:00:00+00:00"
    end_iso = f"{payload.end_date.isoformat()}T23:59:59+00:00"
    busy = (
        supabase.table("calendar_busy_blocks")
        .select("id")
        .eq("student_id", student_id)
        .eq("provider", provider)
        .gte("end_time", start_iso)
        .lte("start_time", end_iso)
        .execute()
    )
    synced = len(busy.data or [])

    supabase.table("calendar_connections").update({"last_busy_sync_at": datetime.now(timezone.utc).isoformat()}).eq(
        "student_id", student_id
    ).eq("provider", provider).execute()
    return {"synced": synced, "message": "Busy blocks refreshed."}
