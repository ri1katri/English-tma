import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.deps import get_current_user
from src.config import settings
from src.database import get_db
from src.models.progress import UserWordProgress
from src.models.user import User
from src.models.word import Word
from src.schemas.progress import WordProgressResponse, WordProgressUpdateRequest
from src.schemas.word import WordSearchResponse, WordSenseResponse
from src.services.auth_service import validate_telegram_init_data

router = APIRouter(prefix="/words", tags=["words"])


async def get_optional_user(
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if not x_telegram_init_data:
        return None
    tg_user = validate_telegram_init_data(
        init_data_raw=x_telegram_init_data,
        bot_token=settings.BOT_TOKEN,
    )
    if not tg_user or "id" not in tg_user:
        return None
    telegram_id = int(tg_user["id"])
    stmt = select(User).where(User.telegram_id == telegram_id)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


@router.get(
    "/search",
    response_model=WordSearchResponse,
    status_code=status.HTTP_200_OK,
)
async def search_word(
    query: str = Query(..., min_length=1, description="Word to look up"),
    db: AsyncSession = Depends(get_db),
):
    normalized_query = query.strip().lower()

    stmt = (
        select(Word)
        .options(selectinload(Word.senses))
        .where(Word.lemma == normalized_query)
    )
    result = await db.execute(stmt)
    word_obj = result.scalar_one_or_none()

    if not word_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Word '{normalized_query}' not found",
        )

    sorted_senses = sorted(word_obj.senses, key=lambda s: s.order_index)

    return WordSearchResponse(
        id=word_obj.id,
        word=word_obj.lemma,
        senses=[WordSenseResponse.model_validate(sense) for sense in sorted_senses],
    )


@router.get("/{word_id}/progress", response_model=WordProgressResponse)
async def get_word_progress(
    word_id: uuid.UUID,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user:
        return WordProgressResponse(word_id=word_id, status="new")

    stmt = select(UserWordProgress).where(
        UserWordProgress.user_id == current_user.id,
        UserWordProgress.word_id == word_id,
    )
    result = await db.execute(stmt)
    progress = result.scalar_one_or_none()

    if not progress:
        return WordProgressResponse(word_id=word_id, status="new")

    return WordProgressResponse.model_validate(progress)


@router.post("/{word_id}/progress", response_model=WordProgressResponse)
async def update_word_progress(
    word_id: uuid.UUID,
    payload: WordProgressUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    word_stmt = select(Word).where(Word.id == word_id)
    word_res = await db.execute(word_stmt)
    if not word_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Слово не найдено",
        )

    stmt = select(UserWordProgress).where(
        UserWordProgress.user_id == current_user.id,
        UserWordProgress.word_id == word_id,
    )
    result = await db.execute(stmt)
    progress = result.scalar_one_or_none()

    if progress:
        progress.status = payload.status
        progress.updated_at = func.now()
    else:
        progress = UserWordProgress(
            user_id=current_user.id,
            word_id=word_id,
            status=payload.status,
        )
        db.add(progress)

    await db.commit()
    await db.refresh(progress)

    return WordProgressResponse.model_validate(progress)