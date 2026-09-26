from fastapi import APIRouter, Depends
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.database import get_db
from src.models.dictionary import UserDictionary, UserDictionaryWord
from src.models.progress import UserWordProgress
from src.models.user import User
from src.schemas.user import DashboardStatsResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/dashboard", response_model=DashboardStatsResponse)
async def get_user_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Всего уникальных слов в словарях пользователя
    total_words_stmt = (
        select(func.count(distinct(UserDictionaryWord.word_id)))
        .join(UserDictionary, UserDictionary.id == UserDictionaryWord.user_dictionary_id)
        .where(UserDictionary.user_id == current_user.id)
    )
    total_words_res = await db.execute(total_words_stmt)
    total_words_in_dicts = total_words_res.scalar_one() or 0

    # Распределение по статусам прогресса
    progress_stmt = (
        select(UserWordProgress.status, func.count(UserWordProgress.id))
        .where(UserWordProgress.user_id == current_user.id)
        .group_by(UserWordProgress.status)
    )
    progress_res = await db.execute(progress_stmt)
    status_counts = dict(progress_res.all())

    words_learning = status_counts.get("learning", 0)
    words_mastered = status_counts.get("mastered", 0)
    words_new = status_counts.get("new", 0)

    return DashboardStatsResponse(
        total_words_in_dicts=total_words_in_dicts,
        words_new=words_new,
        words_learning=words_learning,
        words_mastered=words_mastered,
    )