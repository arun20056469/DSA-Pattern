"""Baseline: tables are created by SQLAlchemy metadata in the app.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-11-22
"""

from alembic import op
import sqlalchemy as sa  # noqa: F401


revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing databases were created with Base.metadata.create_all(); this
    # revision only marks that schema so later revisions can be applied.
    pass


def downgrade() -> None:
    pass
