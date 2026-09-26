"""add user cefr fields

Revision ID: 0006_add_user_cefr_fields
Revises: 0005_create_user_word_progress
Create Date: 2026-09-26 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0006_add_user_cefr_fields"
down_revision: Union[str, None] = "0005_create_user_word_progress"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("cefr_level", sa.String(length=8), nullable=True))
    op.add_column("users", sa.Column("placement_score", sa.Integer(), nullable=True))
    op.add_column(
        "users",
        sa.Column("placement_completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "placement_completed_at")
    op.drop_column("users", "placement_score")
    op.drop_column("users", "cefr_level")