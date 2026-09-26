import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.deps import get_current_user
from src.database import get_db
from src.models.dictionary import (
    SystemDictionary,
    SystemDictionaryWord,
    UserDictionary,
    UserDictionaryWord,
)
from src.models.progress import UserWordProgress
from src.models.user import User
from src.models.word import Word
from src.schemas.dictionary import DictionarySummaryResponse
from src.schemas.system_dictionary import (
    SystemDictionaryDetailResponse,
    SystemDictionarySummaryResponse,
)
from src.schemas.word import WordSearchResponse, WordSenseResponse

router = APIRouter(prefix="/system-dictionaries", tags=["system-dictionaries"])


@router.get("", response_model=List[SystemDictionarySummaryResponse])
async def get_system_dictionaries(
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(
            SystemDictionary.id,
            SystemDictionary.slug,
            SystemDictionary.title,
            SystemDictionary.description,
            SystemDictionary.target_level,
            func.count(SystemDictionaryWord.word_id).label("words_count"),
        )
        .outerjoin(
            SystemDictionaryWord,
            SystemDictionary.id == SystemDictionaryWord.system_dictionary_id,
        )
        .where(SystemDictionary.is_active.is_(True))
        .group_by(SystemDictionary.id)
        .order_by(SystemDictionary.title.asc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        SystemDictionarySummaryResponse(
            id=row.id,
            slug=row.slug,
            title=row.title,
            description=row.description,
            target_level=row.target_level,
            words_count=row.words_count,
        )
        for row in rows
    ]


@router.get("/{dictionary_id}", response_model=SystemDictionaryDetailResponse)
async def get_system_dictionary_detail(
    dictionary_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(SystemDictionary)
        .options(
            selectinload(SystemDictionary.words)
            .selectinload(SystemDictionaryWord.word)
            .selectinload(Word.senses)
        )
        .where(
            SystemDictionary.id == dictionary_id,
            SystemDictionary.is_active.is_(True),
        )
    )
    result = await db.execute(stmt)
    sys_dict = result.scalar_one_or_none()

    if not sys_dict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Системный словарь не найден",
        )

    words_response: List[WordSearchResponse] = []
    for item in sys_dict.words:
        w = item.word
        sorted_senses = sorted(w.senses, key=lambda s: s.order_index)
        words_response.append(
            WordSearchResponse(
                id=w.id,
                word=w.lemma,
                senses=[WordSenseResponse.model_validate(s) for s in sorted_senses],
            )
        )

    return SystemDictionaryDetailResponse(
        id=sys_dict.id,
        slug=sys_dict.slug,
        title=sys_dict.title,
        description=sys_dict.description,
        target_level=sys_dict.target_level,
        words=words_response,
    )


@router.post(
    "/{dictionary_id}/copy",
    response_model=DictionarySummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def copy_system_dictionary(
    dictionary_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(SystemDictionary)
        .options(selectinload(SystemDictionary.words))
        .where(
            SystemDictionary.id == dictionary_id,
            SystemDictionary.is_active.is_(True),
        )
    )
    result = await db.execute(stmt)
    sys_dict = result.scalar_one_or_none()

    if not sys_dict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Системный словарь не найден",
        )

    base_title = sys_dict.title
    candidate_title = base_title
    copy_index = 1

    while True:
        check_stmt = select(UserDictionary.id).where(
            UserDictionary.user_id == current_user.id,
            UserDictionary.title == candidate_title,
        )
        existing = await db.execute(check_stmt)
        if not existing.scalar_one_or_none():
            break
        copy_index += 1
        candidate_title = f"{base_title} ({copy_index})"

    new_user_dict = UserDictionary(
        user_id=current_user.id,
        title=candidate_title,
        description=sys_dict.description,
        origin_system_id=sys_dict.id,
    )
    db.add(new_user_dict)
    await db.flush()

    for item in sys_dict.words:
        link = UserDictionaryWord(
            user_dictionary_id=new_user_dict.id,
            word_id=item.word_id,
        )
        db.add(link)

        # Автоматическая инициализация прогресса слова, если его ещё нет
        progress_stmt = select(UserWordProgress).where(
            UserWordProgress.user_id == current_user.id,
            UserWordProgress.word_id == item.word_id,
        )
        progress_res = await db.execute(progress_stmt)
        if not progress_res.scalar_one_or_none():
            db.add(
                UserWordProgress(
                    user_id=current_user.id,
                    word_id=item.word_id,
                    status="new",
                )
            )

    await db.commit()
    await db.refresh(new_user_dict)

    return DictionarySummaryResponse(
        id=new_user_dict.id,
        title=new_user_dict.title,
        description=new_user_dict.description,
        words_count=len(sys_dict.words),
        created_at=new_user_dict.created_at,
    )