from datetime import date, datetime, timedelta, timezone
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


def test_rename_domain_updates_the_domain_name(api_client: TestClient) -> None:
    domain = api_client.get("/api/domains").json()[0]

    response = api_client.patch(
        f"/api/domains/{domain['id']}", json={"name": "Movement"}
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Movement"
    assert api_client.get("/api/domains").json()[0]["name"] == "Movement"


def test_rename_domain_rejects_duplicate_and_blank_names(
    api_client: TestClient,
) -> None:
    domains = api_client.get("/api/domains").json()

    duplicate = api_client.patch(
        f"/api/domains/{domains[0]['id']}", json={"name": domains[1]["name"]}
    )
    blank = api_client.patch(
        f"/api/domains/{domains[0]['id']}", json={"name": "   "}
    )

    assert duplicate.status_code == 409
    assert blank.status_code == 422


def test_reorder_domains_updates_positions(api_client: TestClient) -> None:
    domains = api_client.get("/api/domains").json()
    reversed_ids = [domain["id"] for domain in reversed(domains)]

    response = api_client.put(
        "/api/domains/order", json={"domain_ids": reversed_ids}
    )

    assert response.status_code == 200
    assert [domain["id"] for domain in response.json()] == reversed_ids
    assert [domain["position"] for domain in response.json()] == list(
        range(len(domains))
    )
    assert [domain["id"] for domain in api_client.get("/api/domains").json()] == reversed_ids


def test_reorder_domains_requires_each_domain_exactly_once(
    api_client: TestClient,
) -> None:
    domains = api_client.get("/api/domains").json()

    response = api_client.put(
        "/api/domains/order",
        json={"domain_ids": [domain["id"] for domain in domains[:-1]]},
    )

    assert response.status_code == 422


def test_domain_without_kpis_has_no_score_or_trend(api_client: TestClient) -> None:
    domain = next(
        item
        for item in api_client.get("/api/domains").json()
        if item["key"] == "other"
    )

    response = api_client.get(f"/api/domains/{domain['id']}/summary")

    assert response.status_code == 200
    assert response.json()["score_percent"] is None
    assert response.json()["month_over_month_change_pp"] is None
    assert response.json()["year_over_year_change_pp"] is None
    assert response.json()["kpis"] == []


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


def test_domain_summary_calculates_monthly_scores_and_trends(
    api_client: TestClient, db_session: Session
) -> None:
    payload = create_payload(api_client)
    payload["target"] = 100
    created = api_client.post("/api/kpis", json=payload).json()
    goal = db_session.get(Goal, UUID(created["id"]))
    assert goal is not None

    today = datetime.now(timezone.utc).date()
    current_month = date(today.year, today.month, 1)

    def month_start(offset: int) -> date:
        month_index = current_month.year * 12 + current_month.month - 1 + offset
        return date(month_index // 12, month_index % 12 + 1, 1)

    fact_dates_and_values = [
        (month_start(-1) + timedelta(days=1), 50),
        (month_start(-1) + timedelta(days=10), 80),
        (month_start(-2) + timedelta(days=1), 40),
        (month_start(-13) + timedelta(days=1), 60),
        (month_start(0) + timedelta(days=1), 100),
    ]
    db_session.add_all(
        Fact(
            user_id=goal.user_id,
            source_app="manual",
            metric_type=goal.metric_type,
            value=value,
            unit="steps",
            observed_at=datetime.combine(
                observed_date, datetime.min.time(), tzinfo=timezone.utc
            ),
        )
        for observed_date, value in fact_dates_and_values
    )
    db_session.flush()

    response = api_client.get(f"/api/domains/{goal.domain_id}/summary")

    assert response.status_code == 200
    summary = response.json()
    assert summary["last_completed_month"] == month_start(-1).strftime("%Y-%m")
    assert summary["score_percent"] == 80
    assert summary["month_over_month_change_pp"] == 40
    assert summary["year_over_year_change_pp"] == 20
    assert summary["kpis"][0]["value"] == 80
    assert summary["kpis"][0]["period_score_percent"] == 80


def test_domain_summary_excludes_missing_values_and_scores_zero_for_at_most(
    api_client: TestClient, db_session: Session
) -> None:
    payload = create_payload(api_client)
    payload.update(name="Lower is better", target=10, direction="at_most")
    created = api_client.post("/api/kpis", json=payload).json()
    missing_payload = create_payload(api_client)
    missing_payload["domain_id"] = payload["domain_id"]
    missing = api_client.post("/api/kpis", json=missing_payload).json()
    goal = db_session.get(Goal, UUID(created["id"]))
    assert goal is not None

    today = datetime.now(timezone.utc).date()
    this_month = date(today.year, today.month, 1)
    month_index = this_month.year * 12 + this_month.month - 2
    last_month = date(month_index // 12, month_index % 12 + 1, 1)
    db_session.add(
        Fact(
            user_id=goal.user_id,
            source_app="manual",
            metric_type=goal.metric_type,
            value=0,
            unit="steps",
            observed_at=datetime.combine(
                last_month + timedelta(days=1),
                datetime.min.time(),
                tzinfo=timezone.utc,
            ),
        )
    )
    db_session.flush()

    response = api_client.get(f"/api/domains/{goal.domain_id}/summary")

    assert response.status_code == 200
    summary = response.json()
    assert summary["score_percent"] == 100
    assert len(summary["kpis"]) == 2
    assert summary["kpis"][0]["period_score_percent"] == 100
    missing_kpi = next(kpi for kpi in summary["kpis"] if kpi["id"] == missing["id"])
    assert missing_kpi["has_value"] is False
    assert missing_kpi["period_score_percent"] is None


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
