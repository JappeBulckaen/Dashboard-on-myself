"""Seed the demo account with five weeks of example check-in KPI history."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db import SessionLocal
from app.main import ensure_default_domains, get_demo_user
from app.models import CheckIn, Goal, LifeDomain, MetricCatalog


def main() -> None:
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=34)
    with SessionLocal() as db:
        user = get_demo_user(db)
        ensure_default_domains(db, user)
        health_domain = db.execute(
            select(LifeDomain).where(
                LifeDomain.user_id == user.id,
                LifeDomain.key == "health_fitness",
            )
        ).scalar_one()

        samples = (
            ("demo.steps_daily_checkin", "Steps", 8000, "steps"),
            ("demo.water_daily_checkin", "Glasses of water", 8, "glasses"),
        )
        created_goals = 0
        added_checkins = 0
        for metric_type, name, target, unit in samples:
            metric = db.get(MetricCatalog, metric_type)
            if metric is None:
                metric = MetricCatalog(
                    metric_type=metric_type,
                    display_name=name,
                    category="manual",
                    default_unit=unit,
                    description="Five-week demo data; each check-in records whether the target was met.",
                )
                db.add(metric)
                db.flush()
            else:
                metric.display_name = name
                metric.default_unit = unit

            goal = db.execute(
                select(Goal).where(
                    Goal.user_id == user.id,
                    Goal.metric_type == metric_type,
                    Goal.period == "all_time",
                )
            ).scalar_one_or_none()
            if goal is None:
                goal = Goal(
                    user_id=user.id,
                    metric_type=metric_type,
                    domain_id=health_domain.id,
                    target_value=target,
                    direction="at_least",
                    tracking_mode="checkin",
                    checkin_cadence="daily",
                    schedule_start_date=start_date,
                    period="all_time",
                )
                db.add(goal)
                db.flush()
                created_goals += 1
            elif (
                goal.tracking_mode != "checkin"
                or goal.checkin_cadence != "daily"
                or goal.domain_id != health_domain.id
                or float(goal.target_value) != target
            ):
                raise RuntimeError(
                    f"Existing KPI {metric_type!r} does not match the demo seed definition; "
                    "refusing to overwrite it."
                )

            for days_ago in range(35):
                checkin_date = today - timedelta(days=days_ago)
                existing = db.execute(
                    select(CheckIn.id).where(
                        CheckIn.goal_id == goal.id,
                        CheckIn.user_id == user.id,
                        CheckIn.checkin_date == checkin_date,
                    )
                ).scalar_one_or_none()
                if existing is not None:
                    continue

                offset = (checkin_date - start_date).days
                if metric_type == "demo.steps_daily_checkin":
                    met = checkin_date.weekday() != 1 and offset % 14 != 6
                else:
                    met = offset not in {8, 25}
                db.add(
                    CheckIn(
                        goal_id=goal.id,
                        user_id=user.id,
                        checkin_date=checkin_date,
                        met=met,
                    )
                )
                added_checkins += 1

        db.commit()
        print(
            f"Demo check-in data ready: {created_goals} KPI(s) created, "
            f"{added_checkins} check-in(s) added, dates {start_date} through {today}."
        )


if __name__ == "__main__":
    main()
