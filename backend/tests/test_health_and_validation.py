import pytest
from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "target": 10},
        {"name": "Valid name", "target": 0},
        {"name": "Valid name", "target": -1},
        {"name": "Valid name"},
        {"name": "Valid name", "target": 10, "value": -1},
        {"name": "x" * 65, "target": 10},
        {"name": "Valid name", "target": 10, "unit": "x" * 21},
    ],
)
def test_create_rejects_invalid_payload(client: TestClient, payload: dict) -> None:
    response = client.post("/api/kpis", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize("method", ["put", "delete"])
def test_kpi_routes_reject_malformed_uuid(client: TestClient, method: str) -> None:
    if method == "put":
        response = client.put("/api/kpis/not-a-uuid", json={})
    else:
        response = client.delete("/api/kpis/not-a-uuid")

    assert response.status_code == 422
