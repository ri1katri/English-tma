import uuid
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.models.base import Base


class SystemDictionary(Base):
    __tablename__ = "system_dictionaries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    slug: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    target_level: Mapped[Optional[str]] = mapped_column(
        String(8),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    words: Mapped[List["SystemDictionaryWord"]] = relationship(
        "SystemDictionaryWord",
        back_populates="dictionary",
        cascade="all, delete-orphan",
    )


class SystemDictionaryWord(Base):
    __tablename__ = "system_dictionary_words"

    system_dictionary_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("system_dictionaries.id", ondelete="CASCADE"),
        primary_key=True,
    )
    word_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("words.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    dictionary: Mapped["SystemDictionary"] = relationship(
        "SystemDictionary",
        back_populates="words",
    )
    word: Mapped["Word"] = relationship("Word")  # type: ignore # noqa: F821


class UserDictionary(Base):
    __tablename__ = "user_dictionaries"
    __table_args__ = (
        UniqueConstraint("user_id", "title", name="uq_user_dictionaries_user_title"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    origin_system_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("system_dictionaries.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    words: Mapped[List["UserDictionaryWord"]] = relationship(
        "UserDictionaryWord",
        back_populates="dictionary",
        cascade="all, delete-orphan",
    )


class UserDictionaryWord(Base):
    __tablename__ = "user_dictionary_words"

    user_dictionary_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_dictionaries.id", ondelete="CASCADE"),
        primary_key=True,
    )
    word_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("words.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    added_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    dictionary: Mapped["UserDictionary"] = relationship(
        "UserDictionary",
        back_populates="words",
    )
    word: Mapped["Word"] = relationship("Word")  # type: ignore # noqa: F821