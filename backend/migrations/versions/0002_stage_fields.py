"""Add curriculum stage and LeetCode metadata fields.

Revision ID: 0002_stage_fields
Revises: 0001_baseline
Create Date: 2026-11-22
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_stage_fields"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "patterns",
        sa.Column("stage", sa.String(20), nullable=False, server_default="BASIC"),
    )
    op.add_column("problems", sa.Column("leetcode_id", sa.Integer(), nullable=True))
    op.add_column("problems", sa.Column("leetcode_slug", sa.String(200), nullable=True))
    op.add_column("problems", sa.Column("tags", sa.Text(), nullable=True))

    # Backfill stages from the existing curriculum order:
    # 1-7 Basic, 8-14 Intermediate, 15-21 Advanced.
    op.execute(
        """
        UPDATE patterns
        SET stage = CASE
            WHEN order_index <= 7 THEN 'BASIC'
            WHEN order_index <= 14 THEN 'INTERMEDIATE'
            ELSE 'ADVANCED'
        END
        """
    )


def downgrade() -> None:
    op.drop_column("problems", "tags")
    op.drop_column("problems", "leetcode_slug")
    op.drop_column("problems", "leetcode_id")
    op.drop_column("patterns", "stage")
