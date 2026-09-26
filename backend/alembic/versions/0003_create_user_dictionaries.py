"""create user dictionaries tables

Revision ID: 0003_create_user_dictionaries
Revises: 0002_create_users
Create Date: 2026-09-25 22:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_create_user_dictionaries"
down_revision: Union[str, None] = "0002_create_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_dictionaries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "title", name="uq_user_dictionaries_user_title"),
    )
    op.create_index(
        op.f("ix_user_dictionaries_user_id"),
        "user_dictionaries",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "user_dictionary_words",
        sa.Column("user_dictionary_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("word_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_dictionary_id"], ["user_dictionaries.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["word_id"], ["words.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_dictionary_id", "word_id"),
    )
    op.create_index(
        op.f("ix_user_dictionary_words_word_id"),
        "user_dictionary_words",
        ["word_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_user_dictionary_words_word_id"), table_name="user_dictionary_words"
    )
    op.drop_table("user_dictionary_words")
    op.drop_index(
        op.f("ix_user_dictionaries_user_id"), table_name="user_dictionaries"
    )
    op.drop_table("user_dictionaries")