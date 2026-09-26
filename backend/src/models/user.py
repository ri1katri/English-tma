import uuid
from typing import Optional
from sqlalchemy import BigInteger, DateTime, Integer, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from src.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        index=True,
        nullable=False,
    )
    first_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    last_name: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    username: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    cefr_level: Mapped[Optional[str]] = mapped_column(
        String(8),
        nullable=True,
    )
    placement_score: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    placement_completed_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
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