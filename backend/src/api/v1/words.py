import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import get_db
from src.models.word import Word, WordSense
from src.services.word_lookup import (
    InvalidWordError,
    LookupStatus,
    ParsedSense,
    clean_translations_ru,
    fetch_external_entries,
    normalize_lemma,
    parse_entries,
)

router = APIRouter(prefix="/words", tags=["words"])


class WordSenseResponse(BaseModel):
    id: uuid.UUID
    part_of_speech: str
    transcription: Optional[str] = None
    translations_ru: List[str]
    definition_en: str
    example_en: Optional[str] = None
    example_ru: Optional[str] = None
    synonyms: List[str]
    order_index: int

    model_config = ConfigDict(from_attributes=True)


class WordSearchResponse(BaseModel):
    id: uuid.UUID
    word: str
    senses: List[WordSenseResponse]

    model_config = ConfigDict(from_attributes=True)


def _error(status_code: int, code: str, message: str) -> HTTPException:
    # Фронтенд смотрит на detail.code; технических деталей провайдера здесь нет.
    return HTTPException(
        status_code=status_code, detail={"code": code, "message": message}
    )


async def _load_word(
    db: AsyncSession, lemma: str, *, refresh: bool = False
) -> Optional[Word]:
    stmt = select(Word).options(selectinload(Word.senses)).where(Word.lemma == lemma)
    if refresh:
        # Не брать устаревшее состояние из identity map сессии.
        stmt = stmt.execution_options(populate_existing=True)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _build_response(word: Word) -> WordSearchResponse:
    return WordSearchResponse(
        id=word.id,
        word=word.lemma,
        senses=[
            WordSenseResponse(
                id=s.id,
                part_of_speech=s.part_of_speech,
                transcription=s.transcription,
                # только русские строки: старые «переводы» вида ["apple"] не показываем
                translations_ru=clean_translations_ru(s.translations_ru),
                definition_en=s.definition_en,
                example_en=s.example_en,
                example_ru=s.example_ru,
                synonyms=[x for x in (s.synonyms or []) if isinstance(x, str)],
                order_index=s.order_index,
            )
            for s in word.senses
        ],
    )


async def _store_word_with_senses(
    db: AsyncSession, lemma: str, parsed: List[ParsedSense]
) -> Word:
    """
    Сохраняет слово и его значения так, чтобы параллельные запросы не создали
    дубликаты ни words, ни word_senses:

      1. INSERT ... ON CONFLICT (lemma) DO NOTHING — одна запись words на lemma
         (UNIQUE-индекс на words.lemma).
      2. SELECT ... FOR UPDATE по этой строке — конкурирующие запросы ждут здесь.
      3. Значения добавляем только если у слова их ещё нет: тот, кто вошёл
         вторым, после снятия блокировки увидит значения первого и ничего не добавит.
    """
    await db.execute(
        pg_insert(Word.__table__)
        .values(lemma=lemma)
        .on_conflict_do_nothing(index_elements=["lemma"])
    )
    locked = await db.execute(
        select(Word.id).where(Word.lemma == lemma).with_for_update()
    )
    word_id = locked.scalar_one()

    existing = await db.execute(
        select(func.count()).select_from(WordSense).where(WordSense.word_id == word_id)
    )
    if existing.scalar_one() == 0:
        db.add_all(
            [
                WordSense(
                    word_id=word_id,
                    part_of_speech=p.part_of_speech,
                    transcription=p.transcription,
                    translations_ru=list(p.translations_ru),  # внешний API их не даёт
                    definition_en=p.definition_en,
                    example_en=p.example_en,
                    example_ru=None,
                    synonyms=list(p.synonyms),
                    order_index=i,
                )
                for i, p in enumerate(parsed)
            ]
        )
    await db.commit()

    word = await _load_word(db, lemma, refresh=True)
    if word is None:
        raise RuntimeError("Word disappeared right after being stored")
    return word


@router.get("/search", response_model=WordSearchResponse)
async def search_word(
    query: str = Query(..., min_length=1, max_length=200, description="Английское слово"),
    db: AsyncSession = Depends(get_db),
):
    try:
        lemma = normalize_lemma(query)
    except InvalidWordError:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "invalid_input",
            "Введите одно английское слово латинскими буквами",
        )

    # 1. Наша БД — единственный источник для уже известных слов.
    word = await _load_word(db, lemma)
    if word is not None and word.senses:
        return _build_response(word)

    # 2. Слова нет (или у него нет значений) — спрашиваем внешний словарь.
    lookup = await fetch_external_entries(lemma)

    if lookup.status is LookupStatus.UNAVAILABLE:
        # НЕ «слово не найдено»: сервис просто не ответил, в БД ничего не пишем.
        raise _error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "provider_unavailable",
            "Словарный сервис временно недоступен. Попробуйте позже",
        )

    parsed = parse_entries(lookup.entries, lemma) if lookup.status is LookupStatus.FOUND else []
    if not parsed:
        raise _error(
            status.HTTP_404_NOT_FOUND,
            "word_not_found",
            f"Слово «{lemma}» не найдено в словаре",
        )

    word = await _store_word_with_senses(db, lemma, parsed)
    return _build_response(word)
