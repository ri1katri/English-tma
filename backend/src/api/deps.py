import logging
from typing import Any, Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_db
from src.models.user import User
from src.services.auth_service import (
    extract_telegram_id,
    validate_telegram_init_data,
)
from src.services.user_service import get_or_create_user

logger = logging.getLogger(__name__)

# Значение, которое текущий фронтенд шлёт вне Telegram (браузер).
# Принимается ТОЛЬКО при DEV_AUTH_BYPASS=true.
DEV_DEMO_HEADER_VALUE = "demo_mode"


def _unauthorized() -> HTTPException:
    # Одно и то же сообщение для всех причин: не подсказываем, что именно не так
    # (подпись, срок, формат). Подробности — в логах, без самих данных.
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing Telegram authentication data",
    )


async def get_current_user(
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Единственное место, где определяется «кто делает запрос».
    Пользователь берётся ТОЛЬКО из проверенной подписи Telegram initData.
    Никаких автоматических demo-пользователей: любая проблема → 401/500/503.
    """
    if not settings.BOT_TOKEN:
        logger.error("BOT_TOKEN is not configured; cannot authenticate requests")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server authentication is not configured",
        )

    init_data = (x_telegram_init_data or "").strip()
    tg_user: Any

    if settings.DEV_AUTH_BYPASS and init_data in ("", DEV_DEMO_HEADER_VALUE):
        # Явный dev-режим (по умолчанию выключен). Подделанный/просроченный
        # initData сюда не попадает — он идёт по обычной проверке ниже.
        tg_user = {
            "id": settings.DEV_AUTH_TELEGRAM_ID,
            "first_name": "Dev User",
            "username": "dev_user",
        }
    else:
        if not init_data:
            logger.warning("Auth rejected: X-Telegram-Init-Data header is missing")
            raise _unauthorized()

        tg_user = validate_telegram_init_data(
            init_data_raw=init_data,
            bot_token=settings.BOT_TOKEN,
        )
        if not tg_user:
            logger.warning("Auth rejected: initData failed validation")
            raise _unauthorized()

    telegram_id = extract_telegram_id(tg_user)
    if telegram_id is None:
        logger.warning("Auth rejected: Telegram user object has no valid id")
        raise _unauthorized()

    try:
        return await get_or_create_user(
            db,
            telegram_id=telegram_id,
            first_name=tg_user.get("first_name"),
            last_name=tg_user.get("last_name"),
            username=tg_user.get("username"),
        )
    except SQLAlchemyError:
        # Ошибка БД — это НЕ повод «пустить как demo». Отвечаем 503.
        await db.rollback()
        logger.exception("Database error while resolving current user")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is temporarily unavailable",
        )
