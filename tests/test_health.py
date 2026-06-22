from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_v1():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "pharmagnostic-backend"
    assert payload["backend"] == "ok"
    assert payload["database"] in {"connected", "disconnected"}
    assert payload["status"] in {
        "API disponible",
        "API disponible con problemas de base de datos",
    }


def test_health_endpoint_api():
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["backend"] == "ok"
    assert payload["database"] in {"connected", "disconnected"}
