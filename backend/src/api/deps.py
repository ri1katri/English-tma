import json
import urllib.parse
from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_db
from src.models.user import User
from src.services.auth_service import validate_telegram_init_data


async def get_current_user(
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
    db: AsyncSession = Depends(get_db),
) -> User:
    # 1. Попытка официальной валидации Telegram initData
    if x_telegram_init_data:
        try:
            tg_user_data = validate_telegram_init_data(
                init_data_raw=x_telegram_init_data,
                bot_token=settings.BOT_TOKEN,
            )
            if tg_user_data and "id" in tg_user_data:
                stmt = select(User).where(User.telegram_id == tg_user_data["id"])
                res = await db.execute(stmt)
                user = res.scalar_one_or_none()

                if not user:
                    user = User(
                        telegram_id=tg_user_data["id"],
                        first_name=tg_user_data.get("first_name", "Telegram User"),
                        last_name=tg_user_data.get("last_name"),
                        username=tg_user_data.get("username"),
                    )
                    db.add(user)
                    await db.commit()
                    await db.refresh(user)

                return user
        except Exception:
            pass  # При сбое валидации переходим к dev-fallback

    # 2. Мягкий Dev-fallback для браузера / тестирования (telegram_id=999999999)
    dev_tg_id = 999999999
    stmt = select(User).where(User.telegram_id == dev_tg_id)
    res = await db.execute(stmt)
    dev_user = res.scalar_one_or_none()

    if not dev_user:
        dev_user = User(
            telegram_id=dev_tg_id,
            first_name="Demo User",
            last_name="Web",
            username="demo_user",
        )
        db.add(dev_user)
        await db.commit()
        await db.refresh(dev_user)

    return dev_user