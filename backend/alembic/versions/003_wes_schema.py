"""Adopt GA4GH WES schema: rename status→state, add stdout/stderr/exit_code/tags

Revision ID: 003
Revises: 002
Create Date: 2026-03-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Old status → WES state mapping
STATE_MAP = {
    "pending": "QUEUED",
    "running": "RUNNING",
    "completed": "COMPLETE",
    "failed": "EXECUTOR_ERROR",
    "cancelled": "CANCELED",
}


def upgrade() -> None:
    # Add new columns
    op.add_column("jobs", sa.Column("stdout", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("stderr", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("exit_code", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("tags", postgresql.JSONB(), nullable=True))

    # Rename status → state
    op.alter_column("jobs", "status", new_column_name="state")

    # Migrate old status values to WES states
    for old, new in STATE_MAP.items():
        op.execute(f"UPDATE jobs SET state = '{new}' WHERE state = '{old}'")

    # Copy result → stdout, error → stderr for existing rows
    op.execute("UPDATE jobs SET stdout = result WHERE result IS NOT NULL AND stdout IS NULL")
    op.execute("UPDATE jobs SET stderr = error WHERE error IS NOT NULL AND stderr IS NULL")

    # Drop old columns
    op.drop_column("jobs", "result")
    op.drop_column("jobs", "error")


def downgrade() -> None:
    # Re-add old columns
    op.add_column("jobs", sa.Column("result", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("error", sa.Text(), nullable=True))

    # Copy back
    op.execute("UPDATE jobs SET result = stdout WHERE stdout IS NOT NULL")
    op.execute("UPDATE jobs SET error = stderr WHERE stderr IS NOT NULL")

    # Rename state → status
    op.alter_column("jobs", "state", new_column_name="status")

    # Reverse state mapping
    for old, new in STATE_MAP.items():
        op.execute(f"UPDATE jobs SET status = '{old}' WHERE status = '{new}'")

    # Drop new columns
    op.drop_column("jobs", "tags")
    op.drop_column("jobs", "exit_code")
    op.drop_column("jobs", "stderr")
    op.drop_column("jobs", "stdout")
