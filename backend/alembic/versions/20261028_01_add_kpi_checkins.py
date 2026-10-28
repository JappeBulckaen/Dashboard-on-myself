"""Add scheduled KPI check-ins.

Revision ID: 20261028_01
Revises: 20261026_01
Create Date: 2026-10-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261028_01"
down_revision = "20261026_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "goals",
        sa.Column(
            "tracking_mode",
            sa.String(length=20),
            nullable=False,
            server_default="numeric",
        ),
    )
    op.add_column("goals", sa.Column("checkin_cadence", sa.String(length=20), nullable=True))
    op.add_column(
        "goals",
        sa.Column("schedule_weekdays", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("goals", sa.Column("schedule_start_date", sa.Date(), nullable=True))
    op.create_unique_constraint("uq_goals_id_user_id", "goals", ["id", "user_id"])
    op.create_table(
        "checkins",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("goal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checkin_date", sa.Date(), nullable=False),
        sa.Column("met", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["goal_id", "user_id"],
            ["goals.id", "goals.user_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("goal_id", "checkin_date", name="uq_checkins_goal_date"),
    )
    op.create_index("ix_checkins_user_date", "checkins", ["user_id", "checkin_date"])


def downgrade() -> None:
    op.drop_index("ix_checkins_user_date", table_name="checkins")
    op.drop_table("checkins")
    op.drop_constraint("uq_goals_id_user_id", "goals", type_="unique")
    op.drop_column("goals", "schedule_start_date")
    op.drop_column("goals", "schedule_weekdays")
    op.drop_column("goals", "checkin_cadence")
    op.drop_column("goals", "tracking_mode")
