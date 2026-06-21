from fastapi import Header, HTTPException, status

from app.config import settings


async def verify_api_key(x_analytics_key: str | None = Header(None)) -> None:
    """Validate the X-Analytics-Key header for protected endpoints."""
    if x_analytics_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing analytics API key",
            headers={"WWW-Authenticate": "X-Analytics-Key"},
        )

    if x_analytics_key != settings.analytics_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid analytics API key",
        )
