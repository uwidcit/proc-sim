"""Add account_claimed and results_published columns.

Revision ID: 20261022_claimed
Revises:
Create Date: 2026-10-22

Brownfield-safe: uses IF NOT EXISTS on Postgres so existing prod DBs upgrade cleanly.
"""

from alembic import op
import sqlalchemy as sa


revision = "20261022_claimed"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            "ALTER TABLE app_setting "
            "ADD COLUMN IF NOT EXISTS results_published BOOLEAN NOT NULL DEFAULT FALSE"
        )
        op.execute(
            "ALTER TABLE student "
            "ADD COLUMN IF NOT EXISTS account_claimed BOOLEAN NOT NULL DEFAULT TRUE"
        )
        return

    # SQLite / others: add only when missing
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "app_setting" in tables:
        cols = {c["name"] for c in inspector.get_columns("app_setting")}
        if "results_published" not in cols:
            with op.batch_alter_table("app_setting") as batch:
                batch.add_column(
                    sa.Column(
                        "results_published",
                        sa.Boolean(),
                        nullable=False,
                        server_default=sa.false(),
                    )
                )

    if "student" in tables:
        cols = {c["name"] for c in inspector.get_columns("student")}
        if "account_claimed" not in cols:
            with op.batch_alter_table("student") as batch:
                batch.add_column(
                    sa.Column(
                        "account_claimed",
                        sa.Boolean(),
                        nullable=False,
                        server_default=sa.true(),
                    )
                )


def downgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "student" in tables:
        cols = {c["name"] for c in inspector.get_columns("student")}
        if "account_claimed" in cols:
            if dialect == "postgresql":
                op.execute("ALTER TABLE student DROP COLUMN IF EXISTS account_claimed")
            else:
                with op.batch_alter_table("student") as batch:
                    batch.drop_column("account_claimed")

    if "app_setting" in tables:
        cols = {c["name"] for c in inspector.get_columns("app_setting")}
        if "results_published" in cols:
            if dialect == "postgresql":
                op.execute(
                    "ALTER TABLE app_setting DROP COLUMN IF EXISTS results_published"
                )
            else:
                with op.batch_alter_table("app_setting") as batch:
                    batch.drop_column("results_published")
