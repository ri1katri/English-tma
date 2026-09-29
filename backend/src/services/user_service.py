from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User

DEFAULT_FIRST_NAME = "Telegram User"


def _clip(value: Optional[str], max_len: int) -> Optional[str]:
    """Обрезает значение под длину колонки; пустую строку превращает в None."""
    if value is None:
        return None
    return str(value).strip()[:max_len] or None


async def _get_by_telegram_id(db: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_or_create_user(
    db: AsyncSession,
    *,
    telegram_id: int,
    first_name: Optional[str],
    last_name: Optional[str] = None,
    username: Optional[str] = None,
    refresh_profile: bool = False,
) -> User:
    """
    Возвращает пользователя по telegram_id, создавая его при отсутствии.
    Безопасно при параллельных запросах от одного нового пользователя.

    Как устроено:
      1. SELECT — быстрый путь для существующих пользователей (без записи в БД).
      2. Если не найден — INSERT ... ON CONFLICT (telegram_id) DO NOTHING.
         UNIQUE-индекс на users.telegram_id гарантирует, что строка будет одна.
         Если параллельный запрос вставил её первым, наш INSERT дождётся его
         COMMIT и тихо ничего не сделает — без IntegrityError.
      3. COMMIT и повторный SELECT: строка теперь точно есть (наша или чужая).

    refresh_profile=True обновляет имя/username существующего пользователя.
    """
    first_name_clean = _clip(first_name, 128) or DEFAULT_FIRST_NAME
    last_name_clean = _clip(last_name, 128)
    username_clean = _clip(username, 64)

    user = await _get_by_telegram_id(db, telegram_id)

    if user is None:
        await db.execute(
            pg_insert(User.__table__)
            .values(
                telegram_id=telegram_id,
                first_name=first_name_clean,
                last_name=last_name_clean,
                username=username_clean,
            )
            .on_conflict_do_nothing(index_elements=["telegram_id"])
        )
        await db.commit()
        user = await _get_by_telegram_id(db, telegram_id)
        if user is None:
            # Строка не найдена сразу после ON CONFLICT DO NOTHING — не должно
            # происходить (её могли только удалить между двумя запросами).
            raise RuntimeError("Failed to create or load user by telegram_id")
        return user

    if refresh_profile and (
        user.first_name != first_name_clean
        or user.last_name != last_name_clean
        or user.username != username_clean
    ):
        user.first_name = first_name_clean
        user.last_name = last_name_clean
        user.username = username_clean
        await db.commit()

    return user
