from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db import Base


class User(Base):
    """A dashboard account; the current API creates a shared demo account on demand."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, nullable=False, default=True)


class Connection(Base):
    """A user's external data-source connection and its credential metadata."""

    __tablename__ = "connections"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    source_app = Column(String(100), nullable=False)
    provider = Column(String(100), nullable=False)
    access_token_encrypted = Column(Text, nullable=True)
    refresh_token_encrypted = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    scopes = Column(JSON, nullable=True)
    status = Column(String(50), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "source_app", name="uq_connections_user_source"),)


class MetricCatalog(Base):
    """Describes a metric's display name, category, unit, and aggregation behavior."""

    __tablename__ = "metric_catalog"

    metric_type = Column(String(150), primary_key=True)
    display_name = Column(String(200), nullable=False)
    category = Column(String(80), nullable=False)
    default_unit = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    aggregation_type = Column(String(50), nullable=False, default="latest")
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class LifeDomain(Base):
    """A user's life domain used to group their KPIs on the overview."""

    __tablename__ = "life_domains"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    key = Column(String(80), nullable=False)
    name = Column(String(80), nullable=False)
    position = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "key", name="uq_life_domains_user_key"),
        UniqueConstraint("user_id", "name", name="uq_life_domains_user_name"),
        Index("ix_life_domains_user_position", "user_id", "position"),
    )


class Fact(Base):
    """A timestamped observation of a metric from a particular source."""

    __tablename__ = "facts"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    source_app = Column(String(100), nullable=False)
    metric_type = Column(String(150), ForeignKey("metric_catalog.metric_type"), nullable=False)
    value = Column(Numeric(precision=18, scale=6), nullable=False)
    unit = Column(String(50), nullable=True)
    observed_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "source_app", "metric_type", "observed_at", name="uq_facts_user_source_metric_time"),)


class Goal(Base):
    """A user's target for one metric over a selected period."""

    __tablename__ = "goals"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    metric_type = Column(String(150), ForeignKey("metric_catalog.metric_type"), nullable=False)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("life_domains.id", ondelete="RESTRICT"), nullable=False)
    target_value = Column(Numeric(precision=18, scale=6), nullable=False)
    direction = Column(String(20), nullable=False)
    tracking_mode = Column(String(20), nullable=False, default="numeric")
    checkin_cadence = Column(String(20), nullable=True)
    schedule_weekdays = Column(JSON, nullable=True)
    schedule_start_date = Column(Date, nullable=True)
    period = Column(String(50), nullable=False, default="all_time")
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "metric_type", "period", name="uq_goals_user_metric_period"),
        UniqueConstraint("id", "user_id", name="uq_goals_id_user_id"),
    )


class CheckIn(Base):
    """A yes/no answer for one scheduled KPI evaluation date."""

    __tablename__ = "checkins"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    goal_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    checkin_date = Column(Date, nullable=False)
    met = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        ForeignKeyConstraint(
            ["goal_id", "user_id"],
            ["goals.id", "goals.user_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("goal_id", "checkin_date", name="uq_checkins_goal_date"),
        Index("ix_checkins_user_date", "user_id", "checkin_date"),
    )


class DashboardLayout(Base):
    """Saved widget configuration for a user's dashboard."""

    __tablename__ = "dashboard_layout"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    widgets = Column(JSON, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class SyncRun(Base):
    """Status and results for one attempt to import data from a source."""

    __tablename__ = "sync_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    source_app = Column(String(100), nullable=False)
    status = Column(String(30), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    records_processed = Column(String(20), nullable=False, default="0")
