"""initial words and word_senses tables

Revision ID: 0001_initial_words
Revises: 
Create Date: 2026-09-25 16:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_words"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "words",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("lemma", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_words_lemma"), "words", ["lemma"], unique=True)

    op.create_table(
        "word_senses",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("word_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("part_of_speech", sa.String(length=32), nullable=False),
        sa.Column("transcription", sa.String(length=128), nullable=True),
        sa.Column(
            "translations_ru",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("definition_en", sa.Text(), nullable=False),
        sa.Column("example_en", sa.Text(), nullable=True),
        sa.Column("example_ru", sa.Text(), nullable=True),
        sa.Column(
            "synonyms",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("order_index", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["word_id"], ["words.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_word_senses_word_id"),
        "word_senses",
        ["word_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_word_senses_word_id"), table_name="word_senses")
    op.drop_table("word_senses")
    op.drop_index(op.f("ix_words_lemma"), table_name="words")
    op.drop_table("words")