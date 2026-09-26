from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import settings
from src.database import get_db
from src.models.user import User
from src.services.auth_service import validate_telegram_init_data


async def get_current_user(
    x_telegram_init_data: str = Header(..., alias="X-Telegram-Init-Data"),
    db: AsyncSession = Depends(get_db),
) -> User:
    tg_user = validate_telegram_init_data(
        init_data_raw=x_telegram_init_data,
        bot_token=settings.BOT_TOKEN,
    )
    if not tg_user or "id" not in tg_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Telegram initData signature",
        )

    telegram_id = int(tg_user["id"])
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            telegram_id=telegram_id,
            first_name=tg_user.get("first_name", "Anonymous"),
            last_name=tg_user.get("last_name"),
            username=tg_user.get("username"),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user