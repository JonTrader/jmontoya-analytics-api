from uuid import UUID

from httpx import AsyncClient

from app.config import settings

VALID_KEY = settings.analytics_api_key


def _valid_event_payload() -> dict:
    return {
        "event_type": "click",
        "label": "GitHub",
        "pathname": "/projects",
        "device_type": "desktop",
        "session_id": "test-session-1",
    }


async def test_create_event_with_valid_key(client: AsyncClient) -> None:
    response = await client.post(
        "/api/analytics/events",
        json=_valid_event_payload(),
        headers={"X-Analytics-Key": VALID_KEY},
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    UUID(data["id"])  # verify valid UUID
    assert data["event_type"] == "click"
    assert data["label"] == "GitHub"
    assert data["pathname"] == "/projects"
    assert data["device_type"] == "desktop"
    assert data["session_id"] == "test-session-1"


async def test_create_event_missing_key(client: AsyncClient) -> None:
    response = await client.post(
        "/api/analytics/events",
        json=_valid_event_payload(),
    )
    assert response.status_code == 401


async def test_create_event_invalid_key(client: AsyncClient) -> None:
    response = await client.post(
        "/api/analytics/events",
        json=_valid_event_payload(),
        headers={"X-Analytics-Key": "invalid-key"},
    )
    assert response.status_code == 403


async def test_create_event_invalid_payload(client: AsyncClient) -> None:
    response = await client.post(
        "/api/analytics/events",
        json={"event_type": "click"},  # missing required fields
        headers={"X-Analytics-Key": VALID_KEY},
    )
    assert response.status_code == 422
