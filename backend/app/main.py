import re
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Fact, Goal, MetricCatalog, User

app = FastAPI(title="Dashboard on Myself API")


class KpiCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    target: float = Field(..., gt=0)
    unit: Optional[str] = Field(default=None, max_length=20)
    value: Optional[float] = Field(default=None, ge=0)
    metric_type: Optional[str] = None


class KpiUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    target: Optional[float] = Field(default=None, gt=0)
    unit: Optional[str] = Field(default=None, max_length=20)


class KpiRead(BaseModel):
    id: str
    metric_type: str
    name: str
    value: float
    target: float
    unit: Optional[str] = None


def get_demo_user(db: Session) -> User:
    user = db.execute(select(User).where(User.email == "demo@dashboard.local")).scalar_one_or_none()
    if user is None:
        user = User(email="demo@dashboard.local", full_name="Demo User", is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def make_metric_type(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return f"manual.{slug or 'metric'}"


def serialize_goal(db: Session, goal: Goal) -> dict[str, Any]:
    metric = db.get(MetricCatalog, goal.metric_type)
    fact = (
        db.execute(
            select(Fact)
            .where(Fact.user_id == goal.user_id, Fact.metric_type == goal.metric_type)
            .order_by(Fact.observed_at.desc())
            .limit(1)
        )
        .scalar_one_or_none()
    )
    value = float(fact.value) if fact is not None else 0.0
    unit = metric.default_unit if metric and metric.default_unit else (fact.unit if fact is not None else None)
    return {
        "id": str(goal.id),
        "metric_type": goal.metric_type,
        "name": metric.display_name if metric else goal.metric_type,
        "value": value,
        "target": float(goal.target_value),
        "unit": unit,
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/kpis", response_model=list[KpiRead])
def list_kpis():
    db = SessionLocal()
    try:
        user = get_demo_user(db)
        goals = db.execute(select(Goal).where(Goal.user_id == user.id)).scalars().all()
        return [serialize_goal(db, goal) for goal in goals]
    finally:
        db.close()


@app.post("/api/kpis", response_model=KpiRead)
def create_kpi(payload: KpiCreate):
    db = SessionLocal()
    try:
        user = get_demo_user(db)
        metric_type = payload.metric_type or make_metric_type(payload.name)

        metric = db.get(MetricCatalog, metric_type)
        if metric is None:
            metric = MetricCatalog(
                metric_type=metric_type,
                display_name=payload.name,
                category="manual",
                default_unit=payload.unit,
                description="Created in the dashboard MVP",
            )
            db.add(metric)

        goal = Goal(
            user_id=user.id,
            metric_type=metric_type,
            target_value=payload.target,
            direction="at_least",
            period="all_time",
        )
        db.add(goal)
        db.flush()

        if payload.value is not None:
            fact = Fact(
                user_id=user.id,
                source_app="manual",
                metric_type=metric_type,
                value=payload.value,
                unit=payload.unit or metric.default_unit,
                observed_at=datetime.utcnow(),
            )
            db.add(fact)

        db.commit()
        db.refresh(goal)
        return serialize_goal(db, goal)
    finally:
        db.close()


@app.put("/api/kpis/{kpi_id}", response_model=KpiRead)
def update_kpi(kpi_id: str, payload: KpiUpdate):
    db = SessionLocal()
    try:
        goal = db.get(Goal, UUID(kpi_id))
        if goal is None:
            raise HTTPException(status_code=404, detail="KPI not found")

        if payload.name is not None:
            metric = db.get(MetricCatalog, goal.metric_type)
            if metric is not None:
                metric.display_name = payload.name

        if payload.target is not None:
            goal.target_value = payload.target

        if payload.unit is not None:
            metric = db.get(MetricCatalog, goal.metric_type)
            if metric is not None:
                metric.default_unit = payload.unit

        db.commit()
        return serialize_goal(db, goal)
    finally:
        db.close()


@app.delete("/api/kpis/{kpi_id}")
def delete_kpi(kpi_id: str):
    db = SessionLocal()
    try:
        goal = db.get(Goal, UUID(kpi_id))
        if goal is None:
            raise HTTPException(status_code=404, detail="KPI not found")
        db.delete(goal)
        db.commit()
        return {"status": "deleted"}
    finally:
        db.close()
