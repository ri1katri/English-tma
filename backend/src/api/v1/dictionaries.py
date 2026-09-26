import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.deps import get_current_user
from src.database import get_db
from src.models.dictionary import UserDictionary, UserDictionaryWord
from src.models.progress import UserWordProgress
from src.models.user import User
from src.models.word import Word
from src.schemas.dictionary import (
    DictionaryAddWordRequest,
    DictionaryCreateRequest,
    DictionaryDetailResponse,
    DictionarySummaryResponse,
)
from src.schemas.word import WordSearchResponse, WordSenseResponse

router = APIRouter(prefix="/dictionaries", tags=["dictionaries"])


@router.get("", response_model=List[DictionarySummaryResponse])
async def get_user_dictionaries(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(
            UserDictionary.id,
            UserDictionary.title,
            UserDictionary.description,
            UserDictionary.created_at,
            func.count(UserDictionaryWord.word_id).label("words_count"),
        )
        .outerjoin(
            UserDictionaryWord,
            UserDictionary.id == UserDictionaryWord.user_dictionary_id,
        )
        .where(UserDictionary.user_id == current_user.id)
        .group_by(UserDictionary.id)
        .order_by(UserDictionary.created_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        DictionarySummaryResponse(
            id=row.id,
            title=row.title,
            description=row.description,
            words_count=row.words_count,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post("", response_model=DictionarySummaryResponse, status_code=status.HTTP_201_CREATED)
async def create_dictionary(
    payload: DictionaryCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    clean_title = payload.title.strip()
    dictionary = UserDictionary(
        user_id=current_user.id,
        title=clean_title,
        description=payload.description.strip() if payload.description else None,
    )
    db.add(dictionary)
    try:
        await db.commit()
        await db.refresh(dictionary)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Словарь с названием '{clean_title}' уже существует",
        )

    return DictionarySummaryResponse(
        id=dictionary.id,
        title=dictionary.title,
        description=dictionary.description,
        words_count=0,
        created_at=dictionary.created_at,
    )


@router.get("/{dictionary_id}", response_model=DictionaryDetailResponse)
async def get_dictionary_detail(
    dictionary_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(UserDictionary)
        .options(
            selectinload(UserDictionary.words)
            .selectinload(UserDictionaryWord.word)
            .selectinload(Word.senses)
        )
        .where(
            UserDictionary.id == dictionary_id,
            UserDictionary.user_id == current_user.id,
        )
    )
    result = await db.execute(stmt)
    dictionary = result.scalar_one_or_none()

    if not dictionary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Словарь не найден",
        )

    words_response: List[WordSearchResponse] = []
    for item in dictionary.words:
        w = item.word
        sorted_senses = sorted(w.senses, key=lambda s: s.order_index)
        words_response.append(
            WordSearchResponse(
                id=w.id,
                word=w.lemma,
                senses=[WordSenseResponse.model_validate(s) for s in sorted_senses],
            )
        )

    return DictionaryDetailResponse(
        id=dictionary.id,
        title=dictionary.title,
        description=dictionary.description,
        created_at=dictionary.created_at,
        words=words_response,
    )


@router.delete("/{dictionary_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dictionary(
    dictionary_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(UserDictionary).where(
        UserDictionary.id == dictionary_id,
        UserDictionary.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    dictionary = result.scalar_one_or_none()

    if not dictionary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Словарь не найден",
        )

    await db.delete(dictionary)
    await db.commit()
    return None


@router.post("/{dictionary_id}/words", status_code=status.HTTP_200_OK)
async def add_word_to_dictionary(
    dictionary_id: uuid.UUID,
    payload: DictionaryAddWordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(UserDictionary).where(
        UserDictionary.id == dictionary_id,
        UserDictionary.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    dictionary = result.scalar_one_or_none()

    if not dictionary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Словарь не найден",
        )

    word_stmt = select(Word).where(Word.id == payload.word_id)
    word_res = await db.execute(word_stmt)
    word = word_res.scalar_one_or_none()
    if not word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Слово не найдено в глобальном каталоге",
        )

    link_stmt = select(UserDictionaryWord).where(
        UserDictionaryWord.user_dictionary_id == dictionary_id,
        UserDictionaryWord.word_id == payload.word_id,
    )
    link_res = await db.execute(link_stmt)
    existing_link = link_res.scalar_one_or_none()

    if not existing_link:
        new_link = UserDictionaryWord(
            user_dictionary_id=dictionary_id,
            word_id=payload.word_id,
        )
        db.add(new_link)

    # Инициализация статуса прогресса (new), если записи еще нет
    progress_stmt = select(UserWordProgress).where(
        UserWordProgress.user_id == current_user.id,
        UserWordProgress.word_id == payload.word_id,
    )
    progress_res = await db.execute(progress_stmt)
    if not progress_res.scalar_one_or_none():
        new_progress = UserWordProgress(
            user_id=current_user.id,
            word_id=payload.word_id,
            status="new",
        )
        db.add(new_progress)

    await db.commit()
    return {"status": "ok", "message": "Слово добавлено в словарь"}


@router.delete("/{dictionary_id}/words/{word_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_word_from_dictionary(
    dictionary_id: uuid.UUID,
    word_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(UserDictionary).where(
        UserDictionary.id == dictionary_id,
        UserDictionary.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    dictionary = result.scalar_one_or_none()

    if not dictionary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Словарь не найден",
        )

    link_stmt = select(UserDictionaryWord).where(
        UserDictionaryWord.user_dictionary_id == dictionary_id,
        UserDictionaryWord.word_id == word_id,
    )
    link_res = await db.execute(link_stmt)
    link = link_res.scalar_one_or_none()

    if link:
        await db.delete(link)
        await db.commit()

    return None