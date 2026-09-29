import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import settings
from src.database import get_db
from src.schemas.auth import TelegramAuthRequest, UserResponse
from src.services.auth_service import (
    extract_telegram_id,
    validate_telegram_init_data,
)
from src.services.user_service import get_or_create_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/telegram",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def authenticate_telegram(
    payload: TelegramAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    if not settings.BOT_TOKEN:
        logger.error("BOT_TOKEN is not configured; cannot authenticate requests")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server authentication is not configured",
        )

    tg_user = validate_telegram_init_data(
        init_data_raw=payload.init_data,
        bot_token=settings.BOT_TOKEN,
    )
    telegram_id = extract_telegram_id(tg_user)
    if telegram_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Telegram initData signature",
        )

    try:
        return await get_or_create_user(
            db,
            telegram_id=telegram_id,
            first_name=tg_user.get("first_name", "Anonymous"),
            last_name=tg_user.get("last_name"),
            username=tg_user.get("username"),
            refresh_profile=True,
        )
    except SQLAlchemyError:
        await db.rollback()
        logger.exception("Database error while authenticating Telegram user")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is temporarily unavailable",
        )
