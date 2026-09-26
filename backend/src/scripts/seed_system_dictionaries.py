import asyncio
import logging
from sqlalchemy import select
from src.database import async_session_maker
from src.models.dictionary import SystemDictionary, SystemDictionaryWord
from src.models.word import Word

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("seed_system_dictionaries")

SYSTEM_PACKS = [
    {
        "slug": "fruits-and-basics",
        "title": "Fruits & Food Basics",
        "description": "Базовая лексика для описания еды и продуктов питания",
        "target_level": "A1",
        "words": ["apple", "water"],
    },
    {
        "slug": "daily-verbs-movement",
        "title": "Movement & Actions",
        "description": "Ключевые глаголы движения и повседневных действий",
        "target_level": "A2",
        "words": ["run", "play", "break", "fall", "fly", "train"],
    },
    {
        "slug": "essential-b1",
        "title": "Essential Concepts",
        "description": "Многозначные существительные и абстрактные понятия",
        "target_level": "B1",
        "words": ["mind", "sound", "light", "time", "change", "room", "present", "lead"],
    },
]


async def seed_system_dictionaries() -> None:
    async with async_session_maker() as session:
        for pack in SYSTEM_PACKS:
            stmt = select(SystemDictionary).where(SystemDictionary.slug == pack["slug"])
            result = await session.execute(stmt)
            existing_pack = result.scalar_one_or_none()

            if not existing_pack:
                sys_dict = SystemDictionary(
                    slug=pack["slug"],
                    title=pack["title"],
                    description=pack["description"],
                    target_level=pack["target_level"],
                )
                session.add(sys_dict)
                await session.flush()
                logger.info("Created system pack: %s", pack["title"])
            else:
                sys_dict = existing_pack
                sys_dict.title = pack["title"]
                sys_dict.description = pack["description"]
                sys_dict.target_level = pack["target_level"]
                logger.info("Updating existing system pack: %s", pack["title"])

            # Добавляем слова в системный словарь
            for word_lemma in pack["words"]:
                word_stmt = select(Word).where(Word.lemma == word_lemma)
                word_res = await session.execute(word_stmt)
                word = word_res.scalar_one_or_none()

                if word:
                    link_stmt = select(SystemDictionaryWord).where(
                        SystemDictionaryWord.system_dictionary_id == sys_dict.id,
                        SystemDictionaryWord.word_id == word.id,
                    )
                    link_res = await session.execute(link_stmt)
                    if not link_res.scalar_one_or_none():
                        session.add(
                            SystemDictionaryWord(
                                system_dictionary_id=sys_dict.id,
                                word_id=word.id,
                            )
                        )
                else:
                    logger.warning("Word '%s' not found in database, skipped", word_lemma)

        await session.commit()
    logger.info("System dictionaries seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_system_dictionaries())