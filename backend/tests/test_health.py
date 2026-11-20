from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "QueueMind AI" in data["name"]


def test_health_check_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "QueueMind AI" in data["app_name"]
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data


def test_cors_preflight_and_headers_for_frontend_origins():
    """Verify that both ports 5173 and 5174 receive valid CORS headers."""
    for origin in [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]:
        # Preflight OPTIONS request
        options_resp = client.options(
            "/api/v1/health",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert options_resp.status_code == 200
        assert options_resp.headers.get("access-control-allow-origin") == origin

        # Actual GET request with Origin header
        get_resp = client.get("/api/v1/health", headers={"Origin": origin})
        assert get_resp.status_code == 200
        assert get_resp.headers.get("access-control-allow-origin") == origin
        assert get_resp.json()["status"] == "healthy"
