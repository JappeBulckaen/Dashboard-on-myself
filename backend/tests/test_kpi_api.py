from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Fact, Goal


def create_payload(api_client: TestClient) -> dict:
    suffix = uuid4().hex
    domain = next(
        item for item in api_client.get("/api/domains").json()
        if item["key"] == "health_fitness"
    )
    return {
        "name": f"Test KPI {suffix[:8]}",
        "metric_type": f"manual.pytest_{suffix}",
        "target": 10000,
        "unit": "steps",
        "domain_id": domain["id"],
    }


def test_list_kpis_returns_empty_list_for_fresh_test_database(api_client: TestClient) -> None:
    response = api_client.get("/api/kpis")

    assert response.status_code == 200
    assert response.json() == []


def test_list_domains_returns_default_domains_in_order(api_client: TestClient) -> None:
    response = api_client.get("/api/domains")

    assert response.status_code == 200
    assert [domain["key"] for domain in response.json()] == [
        "health_fitness",
        "productivity",
        "finance",
        "relationships",
        "household",
        "other",
    ]


def test_create_kpi_with_initial_value(api_client: TestClient) -> None:
    payload = create_payload(api_client)
    payload["value"] = 7500

    response = api_client.post("/api/kpis", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["metric_type"] == payload["metric_type"]
    assert data["domain_id"] == payload["domain_id"]
    assert data["domain_name"] == "Health & Fitness"
    assert data["direction"] == "at_least"
    assert data["value"] == 7500
    assert data["has_value"] is True
    assert data["target"] == 10000
    assert data["unit"] == "steps"

    listed = api_client.get("/api/kpis")
    assert listed.status_code == 200
    assert any(item["id"] == data["id"] for item in listed.json())


def test_create_kpi_without_initial_value_marks_value_missing(api_client: TestClient) -> None:
    payload = create_payload(api_client)

    response = api_client.post("/api/kpis", json=payload)

    assert response.status_code == 200
    assert response.json()["value"] == 0
    assert response.json()["has_value"] is False


def test_create_kpis_without_explicit_metric_type_get_distinct_metrics(api_client: TestClient) -> None:
    payload = create_payload(api_client)
    payload.pop("metric_type")

    first = api_client.post("/api/kpis", json=payload)
    second = api_client.post("/api/kpis", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["metric_type"] != second.json()["metric_type"]


def test_create_kpi_rejects_duplicate_explicit_metric_type(api_client: TestClient) -> None:
    payload = create_payload(api_client)

    first = api_client.post("/api/kpis", json=payload)
    second = api_client.post("/api/kpis", json=payload)

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"] == "A KPI already exists for this metric"


def test_update_changes_only_supplied_fields(api_client: TestClient) -> None:
    payload = create_payload(api_client)
    payload["value"] = 5000
    created = api_client.post("/api/kpis", json=payload).json()

    response = api_client.put(f"/api/kpis/{created['id']}", json={"target": 12000})

    assert response.status_code == 200
    assert response.json()["target"] == 12000
    assert response.json()["name"] == payload["name"]
    assert response.json()["unit"] == payload["unit"]
    assert response.json()["value"] == 5000


def test_update_missing_kpi_returns_404(api_client: TestClient) -> None:
    response = api_client.put(f"/api/kpis/{uuid4()}", json={"target": 10})

    assert response.status_code == 404


def test_update_can_reassign_domain_and_direction(api_client: TestClient) -> None:
    payload = create_payload(api_client)
    created = api_client.post("/api/kpis", json=payload).json()
    finance = next(
        item for item in api_client.get("/api/domains").json()
        if item["key"] == "finance"
    )

    response = api_client.put(
        f"/api/kpis/{created['id']}",
        json={"domain_id": finance["id"], "direction": "at_most"},
    )

    assert response.status_code == 200
    assert response.json()["domain_id"] == finance["id"]
    assert response.json()["domain_name"] == "Finance"
    assert response.json()["direction"] == "at_most"


def test_create_rejects_domain_not_owned_by_demo_user(api_client: TestClient) -> None:
    payload = create_payload(api_client)
    payload["domain_id"] = str(uuid4())

    response = api_client.post("/api/kpis", json=payload)

    assert response.status_code == 404
    assert response.json()["detail"] == "Life domain not found"


def test_delete_removes_kpi_from_list(api_client: TestClient) -> None:
    created = api_client.post("/api/kpis", json=create_payload(api_client)).json()

    deleted = api_client.delete(f"/api/kpis/{created['id']}")
    listed = api_client.get("/api/kpis")

    assert deleted.status_code == 200
    assert deleted.json() == {"status": "deleted"}
    assert all(item["id"] != created["id"] for item in listed.json())


def test_delete_missing_kpi_returns_404(api_client: TestClient) -> None:
    response = api_client.delete(f"/api/kpis/{uuid4()}")

    assert response.status_code == 404


def test_list_uses_most_recent_fact(api_client: TestClient, db_session: Session) -> None:
    payload = create_payload(api_client)
    payload["value"] = 7000
    created = api_client.post("/api/kpis", json=payload).json()
    goal = db_session.get(Goal, UUID(created["id"]))
    assert goal is not None

    db_session.add(
        Fact(
            user_id=goal.user_id,
            source_app="manual",
            metric_type=goal.metric_type,
            value=8100,
            unit="steps",
            observed_at=datetime.now(timezone.utc) + timedelta(seconds=1),
        )
    )
    db_session.flush()

    response = api_client.get("/api/kpis")
    item = next(kpi for kpi in response.json() if kpi["id"] == created["id"])

    assert item["value"] == 8100
