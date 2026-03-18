"""Add Celery tracking fields to jobs table

Revision ID: 002
Revises: 001
Create Date: 2026-03-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("celery_task_id", sa.String(255), nullable=True))
    op.add_column("jobs", sa.Column("worker_id", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "worker_id")
    op.drop_column("jobs", "celery_task_id")
