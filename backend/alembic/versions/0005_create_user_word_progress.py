"""create user_word_progress table

Revision ID: 0005_create_user_word_progress
Revises: 0004_create_system_dictionaries
Create Date: 2026-09-25 22:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005_create_user_word_progress"
down_revision: Union[str, None] = "0004_create_system_dictionaries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_word_progress",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("word_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'new'"),
            nullable=False,
        ),
        sa.Column("correct_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("incorrect_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("streak_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "next_review_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["word_id"], ["words.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "word_id", name="uq_user_word_progress_user_word"),
    )
    op.create_index(
        op.f("ix_user_word_progress_user_id"),
        "user_word_progress",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_word_progress_word_id"),
        "user_word_progress",
        ["word_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_word_progress_lookup",
        "user_word_progress",
        ["user_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_user_word_progress_lookup", table_name="user_word_progress")
    op.drop_index(op.f("ix_user_word_progress_word_id"), table_name="user_word_progress")
    op.drop_index(op.f("ix_user_word_progress_user_id"), table_name="user_word_progress")
    op.drop_table("user_word_progress")