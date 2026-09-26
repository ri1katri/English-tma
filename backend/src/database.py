from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from src.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    pool_pre_ping=True,      # ПЕРЕПРОВЕРЯЕТ СОЕДИНЕНИЕ ПЕРЕД КАЖДЫМ ЗАПРОСОМ
    pool_recycle=300,        # СБРАСЫВАЕТ СОЕДИНЕНИЯ СТАРШЕ 5 МИНУТ
)

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session