import uuid
from typing import List, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.models.base import Base


class Word(Base):
    __tablename__ = "words"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    lemma: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        index=True,
        nullable=False,
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    senses: Mapped[List["WordSense"]] = relationship(
        "WordSense",
        back_populates="word",
        cascade="all, delete-orphan",
        order_by="WordSense.order_index",
    )


class WordSense(Base):
    __tablename__ = "word_senses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    word_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("words.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    part_of_speech: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    transcription: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    translations_ru: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    definition_en: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    example_en: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    example_ru: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    synonyms: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    order_index: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    word: Mapped["Word"] = relationship(
        "Word",
        back_populates="senses",
    )
    