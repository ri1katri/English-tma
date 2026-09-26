"""create system dictionaries tables and origin_system_id

Revision ID: 0004_create_system_dictionaries
Revises: 0003_create_user_dictionaries
Create Date: 2026-09-25 23:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004_create_system_dictionaries"
down_revision: Union[str, None] = "0003_create_user_dictionaries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "system_dictionaries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_level", sa.String(length=8), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_system_dictionaries_slug"),
        "system_dictionaries",
        ["slug"],
        unique=True,
    )

    op.create_table(
        "system_dictionary_words",
        sa.Column("system_dictionary_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("word_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["system_dictionary_id"], ["system_dictionaries.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["word_id"], ["words.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("system_dictionary_id", "word_id"),
    )
    op.create_index(
        op.f("ix_system_dictionary_words_word_id"),
        "system_dictionary_words",
        ["word_id"],
        unique=False,
    )

    op.add_column(
        "user_dictionaries",
        sa.Column("origin_system_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_user_dictionaries_origin_system_id",
        "user_dictionaries",
        "system_dictionaries",
        ["origin_system_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_user_dictionaries_origin_system_id",
        "user_dictionaries",
        type_="foreignkey",
    )
    op.drop_column("user_dictionaries", "origin_system_id")
    op.drop_index(
        op.f("ix_system_dictionary_words_word_id"),
        table_name="system_dictionary_words",
    )
    op.drop_table("system_dictionary_words")
    op.drop_index(
        op.f("ix_system_dictionaries_slug"),
        table_name="system_dictionaries",
    )
    op.drop_table("system_dictionaries")