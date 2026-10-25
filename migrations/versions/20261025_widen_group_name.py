"""Widen group.groupName so G{n} prefix + display name fits.

Revision ID: 20261025_groupname
Revises: 20261022_claimed
Create Date: 2026-10-25

Brownfield-safe: ALTER COLUMN on Postgres; batch alter elsewhere.
"""

from alembic import op
import sqlalchemy as sa


revision = "20261025_groupname"
down_revision = "20261022_claimed"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("ALTER TABLE \"group\" ALTER COLUMN \"groupName\" TYPE VARCHAR(80)")
        return

    with op.batch_alter_table("group") as batch:
        batch.alter_column(
            "groupName",
            existing_type=sa.String(length=30),
            type_=sa.String(length=80),
            existing_nullable=False,
        )


def downgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("ALTER TABLE \"group\" ALTER COLUMN \"groupName\" TYPE VARCHAR(30)")
        return

    with op.batch_alter_table("group") as batch:
        batch.alter_column(
            "groupName",
            existing_type=sa.String(length=80),
            type_=sa.String(length=30),
            existing_nullable=False,
        )
