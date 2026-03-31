"""Add performance indexes on messages and jobs

Revision ID: 005
Revises: 004
Create Date: 2026-04-01
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use raw SQL with IF NOT EXISTS for idempotency
    op.execute(text("CREATE INDEX IF NOT EXISTS ix_messages_session_seq ON messages(session_id, sequence_num)"))
    op.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_state ON jobs(state)"))


def downgrade() -> None:
    op.drop_index("ix_jobs_state", table_name="jobs")
    op.drop_index("ix_messages_session_seq", table_name="messages")
