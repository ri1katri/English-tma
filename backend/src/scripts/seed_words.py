import asyncio
import json
import logging
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.database import async_session_maker
from src.models.word import Word, WordSense

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("seed_words")

DATA_FILE_PATH = Path(__file__).resolve().parent.parent / "data" / "words_seed.json"


async def seed_data() -> None:
    if not DATA_FILE_PATH.exists():
        logger.error("Data file not found at path: %s", DATA_FILE_PATH)
        sys.exit(1)

    with open(DATA_FILE_PATH, "r", encoding="utf-8") as f:
        words_data = json.load(f)

    logger.info("Read %d words from %s", len(words_data), DATA_FILE_PATH.name)

    created_words = 0
    updated_words = 0

    async with async_session_maker() as session:
        for item in words_data:
            normalized_lemma = item["lemma"].strip().lower()
            senses_data = item.get("senses", [])

            stmt = (
                select(Word)
                .options(selectinload(Word.senses))
                .where(Word.lemma == normalized_lemma)
            )
            result = await session.execute(stmt)
            existing_word = result.scalar_one_or_none()

            if existing_word:
                # Идемпотентность: очищаем старые значения и добавляем актуальные
                existing_word.senses.clear()
                for sense_info in senses_data:
                    sense = WordSense(
                        part_of_speech=sense_info["part_of_speech"],
                        transcription=sense_info.get("transcription"),
                        translations_ru=sense_info.get("translations_ru", []),
                        definition_en=sense_info["definition_en"],
                        example_en=sense_info.get("example_en"),
                        example_ru=sense_info.get("example_ru"),
                        synonyms=sense_info.get("synonyms", []),
                        order_index=sense_info.get("order_index", 0),
                    )
                    existing_word.senses.append(sense)
                updated_words += 1
            else:
                new_word = Word(lemma=normalized_lemma)
                for sense_info in senses_data:
                    sense = WordSense(
                        part_of_speech=sense_info["part_of_speech"],
                        transcription=sense_info.get("transcription"),
                        translations_ru=sense_info.get("translations_ru", []),
                        definition_en=sense_info["definition_en"],
                        example_en=sense_info.get("example_en"),
                        example_ru=sense_info.get("example_ru"),
                        synonyms=sense_info.get("synonyms", []),
                        order_index=sense_info.get("order_index", 0),
                    )
                    new_word.senses.append(sense)
                session.add(new_word)
                created_words += 1

        await session.commit()

    logger.info(
        "Seeding completed successfully! Created words: %d, Updated words: %d",
        created_words,
        updated_words,
    )


if __name__ == "__main__":
    asyncio.run(seed_data())