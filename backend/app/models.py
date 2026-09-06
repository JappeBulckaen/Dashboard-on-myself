from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, JSON, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, nullable=False, default=True)


class Connection(Base):
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
    __tablename__ = "metric_catalog"

    metric_type = Column(String(150), primary_key=True)
    display_name = Column(String(200), nullable=False)
    category = Column(String(80), nullable=False)
    default_unit = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    aggregation_type = Column(String(50), nullable=False, default="latest")
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class Fact(Base):
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
    __tablename__ = "goals"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    metric_type = Column(String(150), ForeignKey("metric_catalog.metric_type"), nullable=False)
    target_value = Column(Numeric(precision=18, scale=6), nullable=False)
    direction = Column(String(20), nullable=False)
    period = Column(String(50), nullable=False, default="all_time")
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "metric_type", "period", name="uq_goals_user_metric_period"),)


class DashboardLayout(Base):
    __tablename__ = "dashboard_layout"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    widgets = Column(JSON, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    source_app = Column(String(100), nullable=False)
    status = Column(String(30), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    records_processed = Column(String(20), nullable=False, default="0")
