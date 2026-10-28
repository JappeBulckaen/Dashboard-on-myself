import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Literal, Optional
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CheckIn, Fact, Goal, LifeDomain, MetricCatalog, User

app = FastAPI(title="Dashboard on Myself API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_DOMAINS = (
    ("health_fitness", "Health & Fitness", 0),
    ("productivity", "Productivity", 1),
    ("finance", "Finance", 2),
    ("relationships", "Relationships", 3),
    ("household", "Household", 4),
    ("other", "Other", 5),
)


class KpiCreate(BaseModel):
    """Fields accepted when creating a KPI and its optional initial value."""

    name: str = Field(..., min_length=1, max_length=64)
    target: float = Field(..., gt=0)
    domain_id: UUID
    direction: Literal["at_least", "at_most"] = "at_least"
    unit: Optional[str] = Field(default=None, max_length=20)
    value: Optional[float] = Field(default=None, ge=0)
    metric_type: Optional[str] = None
    tracking_mode: Literal["numeric", "checkin"] = "numeric"
    checkin_cadence: Optional[Literal["daily", "weekdays", "biweekly"]] = None
    schedule_weekdays: Optional[list[int]] = None
    schedule_start_date: Optional[date] = None

    @model_validator(mode="after")
    def validate_tracking_schedule(self):
        validate_schedule(
            self.tracking_mode,
            self.checkin_cadence,
            self.schedule_weekdays,
            self.schedule_start_date,
        )
        if self.tracking_mode == "checkin" and self.value is not None:
            raise ValueError("Check-in KPIs cannot have an initial numeric value")
        return self


class KpiUpdate(BaseModel):
    """Optional fields that can be changed on an existing KPI."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    target: Optional[float] = Field(default=None, gt=0)
    domain_id: Optional[UUID] = None
    direction: Optional[Literal["at_least", "at_most"]] = None
    unit: Optional[str] = Field(default=None, max_length=20)
    checkin_cadence: Optional[Literal["daily", "weekdays", "biweekly"]] = None
    schedule_weekdays: Optional[list[int]] = None
    schedule_start_date: Optional[date] = None


class KpiRead(BaseModel):
    """KPI representation returned to the dashboard client."""

    id: str
    metric_type: str
    name: str
    domain_id: str
    domain_name: str
    direction: Literal["at_least", "at_most"]
    value: float
    has_value: bool
    target: float
    unit: Optional[str] = None
    tracking_mode: Literal["numeric", "checkin"]
    checkin_cadence: Optional[str] = None
    schedule_weekdays: list[int]
    schedule_start_date: Optional[str] = None
    latest_checkin_on: Optional[str] = None
    latest_checkin_met: Optional[bool] = None


class LifeDomainRead(BaseModel):
    id: str
    key: str
    name: str
    position: int


class LifeDomainUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Domain name cannot be blank")
        return normalized


class LifeDomainOrderUpdate(BaseModel):
    domain_ids: list[UUID] = Field(..., min_length=1)


class CheckInDayRead(BaseModel):
    date: str
    met: Optional[bool]
    recorded: bool
    scheduled: bool


class DomainKpiSummaryRead(KpiRead):
    period_score_percent: Optional[float] = None
    checkin_history: list[CheckInDayRead] = Field(default_factory=list)


class CheckInCreate(BaseModel):
    date: date
    met: bool


class LifeDomainSummaryRead(BaseModel):
    id: str
    key: str
    name: str
    position: int
    last_completed_month: str
    score_percent: Optional[float]
    month_over_month_change_pp: Optional[float]
    year_over_year_change_pp: Optional[float]
    kpis: list[DomainKpiSummaryRead]


def ensure_default_domains(db: Session, user: User) -> None:
    existing_keys = set(
        db.execute(select(LifeDomain.key).where(LifeDomain.user_id == user.id)).scalars().all()
    )
    missing_domains = [
        LifeDomain(user_id=user.id, key=key, name=name, position=position)
        for key, name, position in DEFAULT_DOMAINS
        if key not in existing_keys
    ]
    if missing_domains:
        db.add_all(missing_domains)
        db.commit()


def get_demo_user(db: Session) -> User:
    """Return the shared demo account, creating it the first time it is needed."""
    user = db.execute(select(User).where(User.email == "demo@dashboard.local")).scalar_one_or_none()
    if user is None:
        user = User(email="demo@dashboard.local", full_name="Demo User", is_active=True)
        db.add(user)
        db.flush()
    ensure_default_domains(db, user)
    return user


def get_user_domain(db: Session, user: User, domain_id: UUID) -> LifeDomain:
    domain = db.execute(
        select(LifeDomain).where(LifeDomain.id == domain_id, LifeDomain.user_id == user.id)
    ).scalar_one_or_none()
    if domain is None:
        raise HTTPException(status_code=404, detail="Life domain not found")
    return domain


def get_user_goal(db: Session, user: User, kpi_id: UUID) -> Goal:
    goal = db.execute(
        select(Goal).where(Goal.id == kpi_id, Goal.user_id == user.id)
    ).scalar_one_or_none()
    if goal is None:
        raise HTTPException(status_code=404, detail="KPI not found")
    return goal


def validate_schedule(
    tracking_mode: str,
    cadence: Optional[str],
    weekdays: Optional[list[int]],
    start_date: Optional[date],
) -> None:
    if tracking_mode == "numeric":
        if cadence is not None or weekdays is not None or start_date is not None:
            raise ValueError("Numeric KPIs cannot have a check-in schedule")
        return
    if cadence not in {"daily", "weekdays", "biweekly"}:
        raise ValueError("Check-in KPIs require a supported cadence")
    if weekdays is not None and (
        not weekdays
        or any(day < 0 or day > 6 for day in weekdays)
        or len(set(weekdays)) != len(weekdays)
    ):
        raise ValueError("schedule_weekdays must contain unique weekday values from 0 to 6")
    if cadence == "biweekly" and not weekdays:
        raise ValueError("Biweekly schedules require at least one selected weekday")
    if cadence != "biweekly" and weekdays is not None:
        raise ValueError("Selected weekdays are only valid for biweekly schedules")
    if start_date is None:
        raise ValueError("Check-in schedules require a start date")


def scheduled_checkin_dates(goal: Goal, start: date, end: date) -> list[date]:
    if goal.tracking_mode != "checkin" or goal.schedule_start_date is None:
        return []
    first_day = max(start, goal.schedule_start_date)
    scheduled: list[date] = []
    current = first_day
    while current < end:
        if goal.checkin_cadence == "daily":
            scheduled.append(current)
        elif goal.checkin_cadence == "weekdays" and current.weekday() < 5:
            scheduled.append(current)
        elif goal.checkin_cadence == "biweekly":
            week_number = (current - goal.schedule_start_date).days // 7
            if (
                week_number % 2 == 0
                and current.weekday() in (goal.schedule_weekdays or [])
            ):
                scheduled.append(current)
        current += timedelta(days=1)
    return scheduled


def score_checkins(goal: Goal, checkins: dict[date, CheckIn], start: date, end: date) -> Optional[float]:
    expected_dates = scheduled_checkin_dates(goal, start, end)
    if not expected_dates:
        return None
    yes_count = sum(
        1
        for expected_date in expected_dates
        if (checkin := checkins.get(expected_date)) is not None and checkin.met
    )
    return yes_count / len(expected_dates) * 100


def shift_month(month_start: date, offset: int) -> date:
    month_index = month_start.year * 12 + month_start.month - 1 + offset
    return date(month_index // 12, month_index % 12 + 1, 1)


def progress_percent(value: float, target: float, direction: str) -> float:
    if direction == "at_most":
        ratio = 1.0 if value == 0 else target / value
    else:
        ratio = value / target
    return max(0.0, min(ratio, 1.0)) * 100


def monthly_values(
    facts: list[Fact], start: date, end: date
) -> dict[str, Fact]:
    start_at = datetime.combine(start, time.min, tzinfo=timezone.utc)
    end_at = datetime.combine(end, time.min, tzinfo=timezone.utc)
    latest_by_metric: dict[str, Fact] = {}
    for fact in facts:
        if start_at <= fact.observed_at < end_at:
            latest_by_metric[fact.metric_type] = fact
    return latest_by_metric


def make_metric_type(name: str) -> str:
    """Turn a user-provided metric name into a stable manual metric key."""
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return f"manual.{slug or 'metric'}"


def serialize_goal(db: Session, goal: Goal) -> dict[str, Any]:
    """Combine a goal with its display metadata and most recent recorded value."""
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
    domain = db.get(LifeDomain, goal.domain_id)
    latest_checkin = None
    if goal.tracking_mode == "checkin":
        latest_checkin = db.execute(
            select(CheckIn)
            .where(CheckIn.goal_id == goal.id, CheckIn.user_id == goal.user_id)
            .order_by(CheckIn.checkin_date.desc())
            .limit(1)
        ).scalar_one_or_none()
    value = float(fact.value) if fact is not None else 0.0
    unit = metric.default_unit if metric and metric.default_unit else (fact.unit if fact is not None else None)
    return {
        "id": str(goal.id),
        "metric_type": goal.metric_type,
        "name": metric.display_name if metric else goal.metric_type,
        "domain_id": str(goal.domain_id),
        "domain_name": domain.name,
        "direction": goal.direction,
        "value": value,
        "has_value": fact is not None,
        "target": float(goal.target_value),
        "unit": unit,
        "tracking_mode": goal.tracking_mode,
        "checkin_cadence": goal.checkin_cadence,
        "schedule_weekdays": goal.schedule_weekdays or [],
        "schedule_start_date": (
            goal.schedule_start_date.isoformat()
            if goal.schedule_start_date is not None
            else None
        ),
        "latest_checkin_on": (
            latest_checkin.checkin_date.isoformat()
            if latest_checkin is not None
            else None
        ),
        "latest_checkin_met": latest_checkin.met if latest_checkin is not None else None,
    }


@app.get("/health")
def health_check():
    """Return a simple response for checking that the API process is reachable."""
    return {"status": "ok"}


@app.get("/api/domains", response_model=list[LifeDomainRead])
def list_domains(db: Session = Depends(get_db)):
    """List the demo user's life domains in their configured order."""
    user = get_demo_user(db)
    domains = db.execute(
        select(LifeDomain)
        .where(LifeDomain.user_id == user.id)
        .order_by(LifeDomain.position, LifeDomain.name)
    ).scalars().all()
    return [
        {"id": str(domain.id), "key": domain.key, "name": domain.name, "position": domain.position}
        for domain in domains
    ]


@app.patch("/api/domains/{domain_id}", response_model=LifeDomainRead)
def rename_domain(
    domain_id: UUID, payload: LifeDomainUpdate, db: Session = Depends(get_db)
):
    """Rename one of the demo user's life domains."""
    user = get_demo_user(db)
    domain = get_user_domain(db, user, domain_id)
    duplicate = db.execute(
        select(LifeDomain.id).where(
            LifeDomain.user_id == user.id,
            LifeDomain.name == payload.name,
            LifeDomain.id != domain.id,
        )
    ).scalar_one_or_none()
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="A life domain already has this name")

    domain.name = payload.name
    db.commit()
    db.refresh(domain)
    return {
        "id": str(domain.id),
        "key": domain.key,
        "name": domain.name,
        "position": domain.position,
    }


@app.put("/api/domains/order", response_model=list[LifeDomainRead])
def reorder_domains(
    payload: LifeDomainOrderUpdate, db: Session = Depends(get_db)
):
    """Save a complete ordering of the demo user's life domains."""
    user = get_demo_user(db)
    domains = db.execute(
        select(LifeDomain).where(LifeDomain.user_id == user.id)
    ).scalars().all()
    domains_by_id = {domain.id: domain for domain in domains}
    if (
        len(payload.domain_ids) != len(domains)
        or len(set(payload.domain_ids)) != len(payload.domain_ids)
        or set(payload.domain_ids) != set(domains_by_id)
    ):
        raise HTTPException(
            status_code=422,
            detail="domain_ids must include each life domain exactly once",
        )

    for position, domain_id in enumerate(payload.domain_ids):
        domains_by_id[domain_id].position = position
    db.commit()
    return [
        {
            "id": str(domains_by_id[domain_id].id),
            "key": domains_by_id[domain_id].key,
            "name": domains_by_id[domain_id].name,
            "position": domains_by_id[domain_id].position,
        }
        for domain_id in payload.domain_ids
    ]


@app.get(
    "/api/domains/{domain_id}/summary", response_model=LifeDomainSummaryRead
)
def get_domain_summary(domain_id: UUID, db: Session = Depends(get_db)):
    """Summarize KPI progress for the last completed month and its comparisons."""
    user = get_demo_user(db)
    domain = get_user_domain(db, user, domain_id)
    goals = db.execute(
        select(Goal)
        .where(Goal.user_id == user.id, Goal.domain_id == domain.id)
        .order_by(Goal.created_at, Goal.id)
    ).scalars().all()

    current_month = datetime.now(timezone.utc).date().replace(day=1)
    last_month_start = shift_month(current_month, -1)
    current_month_start = current_month
    previous_month_start = shift_month(last_month_start, -1)
    year_ago_month_start = shift_month(last_month_start, -12)
    metric_types = {goal.metric_type for goal in goals}
    facts: list[Fact] = []
    metrics: dict[str, MetricCatalog] = {}
    checkins_by_goal: dict[UUID, dict[date, CheckIn]] = {}
    if metric_types:
        metrics = {
            metric.metric_type: metric
            for metric in db.execute(
                select(MetricCatalog).where(
                    MetricCatalog.metric_type.in_(metric_types)
                )
            ).scalars()
        }
        facts = db.execute(
            select(Fact)
            .where(
                Fact.user_id == user.id,
                Fact.metric_type.in_(metric_types),
                Fact.observed_at
                >= datetime.combine(year_ago_month_start, time.min, tzinfo=timezone.utc),
                Fact.observed_at
                < datetime.combine(current_month_start, time.min, tzinfo=timezone.utc),
            )
            .order_by(Fact.observed_at)
        ).scalars().all()
        checkin_goals = [goal for goal in goals if goal.tracking_mode == "checkin"]
        if checkin_goals:
            checkin_goal_ids = [goal.id for goal in checkin_goals]
            checkins = db.execute(
                select(CheckIn)
                .where(
                    CheckIn.user_id == user.id,
                    CheckIn.goal_id.in_(checkin_goal_ids),
                    CheckIn.checkin_date >= year_ago_month_start,
                    CheckIn.checkin_date <= datetime.now(timezone.utc).date(),
                )
                .order_by(CheckIn.checkin_date)
            ).scalars().all()
            checkins_by_goal = {goal.id: {} for goal in checkin_goals}
            for checkin in checkins:
                checkins_by_goal[checkin.goal_id][checkin.checkin_date] = checkin

    last_month_values = monthly_values(
        facts, last_month_start, current_month_start
    )
    previous_month_values = monthly_values(
        facts, previous_month_start, last_month_start
    )
    year_ago_values = monthly_values(
        facts, year_ago_month_start, shift_month(year_ago_month_start, 1)
    )

    def score_for_goal(
        goal: Goal,
        values: dict[str, Fact],
        period_checkins: dict[UUID, dict[date, CheckIn]],
        period_start: date,
        period_end: date,
    ) -> Optional[float]:
        if goal.tracking_mode == "checkin":
            return score_checkins(
                goal,
                period_checkins.get(goal.id, {}),
                period_start,
                period_end,
            )
        fact = values.get(goal.metric_type)
        if fact is None:
            return None
        return progress_percent(
            float(fact.value), float(goal.target_value), goal.direction
        )

    def domain_score(
        values: dict[str, Fact],
        period_checkins: dict[UUID, dict[date, CheckIn]],
        period_start: date,
        period_end: date,
    ) -> Optional[float]:
        scores = [
            score
            for goal in goals
            if (
                score := score_for_goal(
                    goal, values, period_checkins, period_start, period_end
                )
            ) is not None
        ]
        return sum(scores) / len(scores) if scores else None

    score = domain_score(
        last_month_values,
        checkins_by_goal,
        last_month_start,
        current_month_start,
    )
    previous_score = domain_score(
        previous_month_values,
        checkins_by_goal,
        previous_month_start,
        last_month_start,
    )
    year_ago_score = domain_score(
        year_ago_values,
        checkins_by_goal,
        year_ago_month_start,
        shift_month(year_ago_month_start, 1),
    )

    kpis = []
    for goal in goals:
        metric = metrics.get(goal.metric_type)
        fact = last_month_values.get(goal.metric_type)
        goal_checkins = checkins_by_goal.get(goal.id, {})
        latest_checkin = max(goal_checkins.values(), key=lambda item: item.checkin_date, default=None)
        period_score = score_for_goal(
            goal,
            last_month_values,
            checkins_by_goal,
            last_month_start,
            current_month_start,
        )
        checkin_history: list[dict[str, Any]] = []
        if goal.tracking_mode == "checkin":
            history_start = datetime.now(timezone.utc).date() - timedelta(days=34)
            history_end = datetime.now(timezone.utc).date() + timedelta(days=1)
            scheduled_dates = set(
                scheduled_checkin_dates(goal, history_start, history_end)
            )
            checkin_history = [
                {
                    "date": history_date.isoformat(),
                    "met": (
                        goal_checkins[history_date].met
                        if history_date in goal_checkins
                        else None
                    ),
                    "recorded": history_date in goal_checkins,
                    "scheduled": history_date in scheduled_dates,
                }
                for history_date in (
                    history_start + timedelta(days=offset)
                    for offset in range((history_end - history_start).days)
                )
            ]
        kpis.append(
            {
                "id": str(goal.id),
                "metric_type": goal.metric_type,
                "name": metric.display_name if metric else goal.metric_type,
                "domain_id": str(domain.id),
                "domain_name": domain.name,
                "direction": goal.direction,
                "value": float(fact.value) if fact is not None else 0.0,
                "has_value": fact is not None,
                "target": float(goal.target_value),
                "unit": metric.default_unit
                if metric and metric.default_unit
                else (fact.unit if fact is not None else None),
                "tracking_mode": goal.tracking_mode,
                "checkin_cadence": goal.checkin_cadence,
                "schedule_weekdays": goal.schedule_weekdays or [],
                "schedule_start_date": (
                    goal.schedule_start_date.isoformat()
                    if goal.schedule_start_date is not None
                    else None
                ),
                "latest_checkin_on": (
                    latest_checkin.checkin_date.isoformat()
                    if latest_checkin is not None
                    else None
                ),
                "latest_checkin_met": (
                    latest_checkin.met if latest_checkin is not None else None
                ),
                "period_score_percent": period_score,
                "checkin_history": checkin_history,
            }
        )

    return {
        "id": str(domain.id),
        "key": domain.key,
        "name": domain.name,
        "position": domain.position,
        "last_completed_month": last_month_start.strftime("%Y-%m"),
        "score_percent": score,
        "month_over_month_change_pp": (
            score - previous_score
            if score is not None and previous_score is not None
            else None
        ),
        "year_over_year_change_pp": (
            score - year_ago_score
            if score is not None and year_ago_score is not None
            else None
        ),
        "kpis": kpis,
    }


@app.get("/api/kpis", response_model=list[KpiRead])
def list_kpis(db: Session = Depends(get_db)):
    """List the demo user's goals as dashboard-ready KPI records."""
    user = get_demo_user(db)
    goals = db.execute(select(Goal).where(Goal.user_id == user.id)).scalars().all()
    return [serialize_goal(db, goal) for goal in goals]


@app.post("/api/kpis", response_model=KpiRead)
def create_kpi(payload: KpiCreate, db: Session = Depends(get_db)):
    """Create a metric definition and goal, plus an initial fact when supplied."""
    user = get_demo_user(db)
    get_user_domain(db, user, payload.domain_id)
    metric_type = payload.metric_type or make_metric_type(payload.name)
    metric = db.get(MetricCatalog, metric_type)
    existing_goal = db.execute(
        select(Goal).where(
            Goal.user_id == user.id,
            Goal.metric_type == metric_type,
            Goal.period == "all_time",
        )
    ).scalar_one_or_none()

    if payload.metric_type and existing_goal is not None:
        raise HTTPException(status_code=409, detail="A KPI already exists for this metric")

    if payload.metric_type is None and metric is not None:
        metric_type = f"{metric_type}_{uuid4().hex}"
        metric = None

    if metric is None:
        metric = MetricCatalog(
            metric_type=metric_type,
            display_name=payload.name,
            category="manual",
            default_unit=payload.unit,
            description="Created in the dashboard MVP",
        )
        db.add(metric)
        db.flush()

    goal = Goal(
        user_id=user.id,
        metric_type=metric_type,
        domain_id=payload.domain_id,
        target_value=payload.target,
        direction=payload.direction,
        tracking_mode=payload.tracking_mode,
        checkin_cadence=payload.checkin_cadence,
        schedule_weekdays=payload.schedule_weekdays,
        schedule_start_date=(
            payload.schedule_start_date
            if payload.tracking_mode == "checkin"
            else None
        ),
        period="all_time",
    )
    db.add(goal)
    # Insert the goal before an optional fact references it.
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


@app.put("/api/kpis/{kpi_id}", response_model=KpiRead)
def update_kpi(kpi_id: UUID, payload: KpiUpdate, db: Session = Depends(get_db)):
    """Update the selected goal or its metric display metadata."""
    user = get_demo_user(db)
    goal = get_user_goal(db, user, kpi_id)

    updated_fields = payload.model_fields_set
    try:
        validate_schedule(
            goal.tracking_mode,
            (
                payload.checkin_cadence
                if "checkin_cadence" in updated_fields
                else goal.checkin_cadence
            ),
            (
                payload.schedule_weekdays
                if "schedule_weekdays" in updated_fields
                else goal.schedule_weekdays
            ),
            (
                payload.schedule_start_date
                if "schedule_start_date" in updated_fields
                else goal.schedule_start_date
            ),
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    if payload.domain_id is not None:
        get_user_domain(db, user, payload.domain_id)
        goal.domain_id = payload.domain_id

    if payload.direction is not None:
        goal.direction = payload.direction

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

    if "checkin_cadence" in updated_fields:
        goal.checkin_cadence = payload.checkin_cadence
    if "schedule_weekdays" in updated_fields:
        goal.schedule_weekdays = payload.schedule_weekdays
    if "schedule_start_date" in updated_fields:
        goal.schedule_start_date = payload.schedule_start_date

    db.commit()
    return serialize_goal(db, goal)


@app.post("/api/kpis/{kpi_id}/checkins", response_model=CheckInDayRead)
def set_kpi_checkin(
    kpi_id: UUID, payload: CheckInCreate, db: Session = Depends(get_db)
):
    """Record or correct a yes/no answer for a scheduled check-in date."""
    user = get_demo_user(db)
    goal = get_user_goal(db, user, kpi_id)
    if goal.tracking_mode != "checkin":
        raise HTTPException(status_code=409, detail="This KPI does not use check-ins")
    today = datetime.now(timezone.utc).date()
    if payload.date > today:
        raise HTTPException(status_code=422, detail="Check-ins cannot be recorded in the future")
    if payload.date not in scheduled_checkin_dates(
        goal, payload.date, payload.date + timedelta(days=1)
    ):
        raise HTTPException(
            status_code=422,
            detail="This date is not scheduled for a check-in",
        )

    checkin = db.execute(
        select(CheckIn).where(
            CheckIn.goal_id == goal.id,
            CheckIn.user_id == user.id,
            CheckIn.checkin_date == payload.date,
        )
    ).scalar_one_or_none()
    if checkin is None:
        checkin = CheckIn(
            goal_id=goal.id,
            user_id=user.id,
            checkin_date=payload.date,
            met=payload.met,
        )
        db.add(checkin)
    else:
        checkin.met = payload.met

    db.commit()
    return {
        "date": checkin.checkin_date.isoformat(),
        "met": checkin.met,
        "recorded": True,
        "scheduled": True,
    }


@app.delete("/api/kpis/{kpi_id}")
def delete_kpi(kpi_id: UUID, db: Session = Depends(get_db)):
    """Delete a goal belonging to the shared demo user's dashboard."""
    user = get_demo_user(db)
    goal = get_user_goal(db, user, kpi_id)
    db.delete(goal)
    db.commit()
    return {"status": "deleted"}
