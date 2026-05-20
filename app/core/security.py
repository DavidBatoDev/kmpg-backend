from fastapi import Header, HTTPException, status

from app.core.config import settings


async def verify_copilot_api_key(x_copilot_api_key: str = Header(...)):
    if x_copilot_api_key != settings.copilot_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Copilot API key",
        )
    return True
