import uuid
from typing import List, Optional
import urllib.parse
from fastapi import APIRouter, Depends, HTTPException, Query, status
import httpx
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import get_db
from src.models.word import Word, WordSense

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


async def fetch_external_word(lemma: str) -> Optional[dict]:
    encoded_word = urllib.parse.quote(lemma)
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{encoded_word}"
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    return data[0]
        except Exception:
            return None
    return None


@router.get("/search", response_model=WordSearchResponse)
async def search_word(
    query: str = Query(..., min_length=1, description="Английское слово"),
    db: AsyncSession = Depends(get_db),
):
    clean_lemma = query.strip().lower()

    # 1. Поиск в локальной базе данных
    stmt = (
        select(Word)
        .options(selectinload(Word.senses))
        .where(Word.lemma == clean_lemma)
    )
    result = await db.execute(stmt)
    word = result.scalar_one_or_none()

    if word and word.senses:
        return WordSearchResponse(
            id=word.id,
            word=word.lemma,
            senses=word.senses,
        )

    # 2. Автоматический Fallback: запрос во внешний Free Dictionary API
    ext_data = await fetch_external_word(clean_lemma)

    if not ext_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Слово «{clean_lemma}» не найдено",
        )

    # Извлечение транскрипции
    transcription = ext_data.get("phonetic")
    if not transcription and ext_data.get("phonetics"):
        for ph in ext_data["phonetics"]:
            if ph.get("text"):
                transcription = ph["text"]
                break

    # Создание или обновление родительского слова
    if not word:
        word = Word(lemma=clean_lemma)
        db.add(word)
        await db.flush()

    senses_to_add: List[WordSense] = []
    order_idx = 0

    meanings = ext_data.get("meanings", [])
    for meaning in meanings:
        pos = meaning.get("part_of_speech", meaning.get("partOfSpeech", "noun"))
        definitions = meaning.get("definitions", [])

        for d in definitions[:2]:
            def_text = d.get("definition", "")
            example_text = d.get("example")
            synonyms = d.get("synonyms", [])[:4]

            if not def_text:
                continue

            sense = WordSense(
                word_id=word.id,
                part_of_speech=pos,
                transcription=transcription,
                translations_ru=[clean_lemma],  # Базовый перевод-транслит/лемма
                definition_en=def_text,
                example_en=example_text,
                example_ru=None,
                synonyms=synonyms,
                order_index=order_idx,
            )
            senses_to_add.append(sense)
            order_idx += 1

    if not senses_to_add:
        sense = WordSense(
            word_id=word.id,
            part_of_speech="noun",
            transcription=transcription,
            translations_ru=[clean_lemma],
            definition_en=f"Definition of {clean_lemma}",
            example_en=None,
            example_ru=None,
            synonyms=[],
            order_index=0,
        )
        senses_to_add.append(sense)

    db.add_all(senses_to_add)
    await db.commit()

    # Загружаем свежие связи
    stmt = (
        select(Word)
        .options(selectinload(Word.senses))
        .where(Word.id == word.id)
    )
    result = await db.execute(stmt)
    saved_word = result.scalar_one()

    return WordSearchResponse(
        id=saved_word.id,
        word=saved_word.lemma,
        senses=saved_word.senses,
    )