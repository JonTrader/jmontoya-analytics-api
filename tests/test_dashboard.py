from httpx import AsyncClient

VALID_KEY = "dev-key-change-in-production"


async def test_dashboard_empty(client: AsyncClient) -> None:
    response = await client.get("/api/analytics/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["total_events"] == 0
    assert data["unique_sessions"] == 0
    assert data["events_by_type"] == {}
    assert data["top_links"] == []
    assert data["top_projects"] == []
    assert data["device_breakdown"] == []
    assert data["top_pages"] == []
    assert data["traffic_sources"] == []
    assert data["events_over_time"] == []
    assert data["average_hover_duration"] is None


async def test_dashboard_with_events(client: AsyncClient) -> None:
    events = [
        {
            "event_type": "click",
            "label": "GitHub",
            "context": "MaxApp",
            "href": "https://github.com/example",
            "pathname": "/projects",
            "device_type": "desktop",
            "session_id": "session-1",
            "referrer": "google.com",
        },
        {
            "event_type": "hover",
            "label": "Demo",
            "context": "MaxApp",
            "pathname": "/projects",
            "device_type": "mobile",
            "session_id": "session-2",
            "duration_ms": 1500,
            "referrer": "google.com",
        },
    ]
    for event in events:
        response = await client.post(
            "/api/analytics/events",
            json=event,
            headers={"X-Analytics-Key": VALID_KEY},
        )
        assert response.status_code == 201

    response = await client.get("/api/analytics/dashboard")
    assert response.status_code == 200
    data = response.json()

    assert data["total_events"] == 2
    assert data["unique_sessions"] == 2
    assert data["events_by_type"] == {"click": 1, "hover": 1}

    top_link_labels = {link["label"] for link in data["top_links"]}
    assert top_link_labels == {"GitHub", "Demo"}

    assert data["top_projects"] == [{"context": "MaxApp", "count": 2}]

    device_types = {device["device_type"] for device in data["device_breakdown"]}
    assert device_types == {"desktop", "mobile"}

    assert data["top_pages"] == [{"pathname": "/projects", "count": 2}]
    assert data["traffic_sources"] == [{"referrer": "google.com", "count": 2}]

    assert len(data["events_over_time"]) == 1
    assert data["events_over_time"][0]["count"] == 2

    assert data["average_hover_duration"] == 1500.0
