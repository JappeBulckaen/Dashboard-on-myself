"""Add life domains and require each KPI to belong to one.

Revision ID: 20261026_01
Revises:
Create Date: 2026-10-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261026_01"
down_revision = None
branch_labels = None
depends_on = None

DEFAULT_DOMAINS = (
    ("health_fitness", "Health & Fitness", 0),
    ("productivity", "Productivity", 1),
    ("finance", "Finance", 2),
    ("relationships", "Relationships", 3),
    ("household", "Household", 4),
    ("other", "Other", 5),
)


def upgrade() -> None:
    op.create_table(
        "life_domains",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "key", name="uq_life_domains_user_key"),
        sa.UniqueConstraint("user_id", "name", name="uq_life_domains_user_name"),
    )
    op.create_index("ix_life_domains_user_position", "life_domains", ["user_id", "position"])
    op.add_column("goals", sa.Column("domain_id", postgresql.UUID(as_uuid=True), nullable=True))

    values = ", ".join(
        "('{}', '{}', {})".format(key, name.replace("'", "''"), position)
        for key, name, position in DEFAULT_DOMAINS
    )
    op.execute(
        sa.text(
            "INSERT INTO life_domains (user_id, key, name, position) "
            "SELECT users.id, defaults.domain_key, defaults.domain_name, defaults.domain_position "
            "FROM users CROSS JOIN (VALUES "
            f"{values}"
            ") AS defaults(domain_key, domain_name, domain_position)"
        )
    )
    op.execute(
        sa.text(
            "UPDATE goals SET domain_id = life_domains.id "
            "FROM life_domains "
            "WHERE life_domains.user_id = goals.user_id AND life_domains.key = 'other'"
        )
    )
    op.alter_column("goals", "domain_id", nullable=False)
    op.create_foreign_key(
        "fk_goals_domain_id_life_domains",
        "goals",
        "life_domains",
        ["domain_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_goals_domain_id_life_domains", "goals", type_="foreignkey")
    op.drop_column("goals", "domain_id")
    op.drop_index("ix_life_domains_user_position", table_name="life_domains")
    op.drop_table("life_domains")
