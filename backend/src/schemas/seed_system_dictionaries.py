import asyncio
import logging
from sqlalchemy import select
from src.database import async_session_maker
from src.models.dictionary import SystemDictionary, SystemDictionaryWord
from src.models.word import Word, WordSense

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("seed_system_dictionaries")

SYSTEM_PACKS = [
    {
        "slug": "cefr-a1-beginner",
        "title": "A1 • Beginner Vocabulary",
        "description": "Базовые слова для первых разговоров и простых описаний",
        "target_level": "A1",
        "words": [
            ("apple", "noun", "/ˈæp.əl/", ["яблоко"], "A round fruit with red or green skin.", "I eat an apple every day.", "Я ем яблоко каждый день."),
            ("water", "noun", "/ˈwɔː.tər/", ["вода"], "A clear liquid essential for life.", "Please give me a glass of water.", "Пожалуйста, дайте мне стакан воды."),
            ("house", "noun", "/haʊs/", ["дом"], "A building for human habitation.", "They live in a beautiful house.", "Они живут в красивом доме."),
            ("friend", "noun", "/frɛnd/", ["друг", "подруга"], "A person you know and like.", "She is my closest friend.", "Она моя самая близкая подруга."),
        ],
    },
    {
        "slug": "cefr-a2-elementary",
        "title": "A2 • Elementary Actions",
        "description": "Повседневные глаголы, действия и путешествия",
        "target_level": "A2",
        "words": [
            ("run", "verb", "/rʌn/", ["бежать", "бегать"], "To move swiftly on foot.", "He runs every morning in the park.", "Он бегает каждое утро в парке."),
            ("watch", "verb", "/wɒtʃ/", ["смотреть", "наблюдать"], "To look attentively at something.", "We watched an interesting film.", "Мы посмотрели интересный фильм."),
            ("train", "noun", "/treɪn/", ["поезд"], "A series of railway carriages.", "The train arrived on time.", "Поезд прибыл вовремя."),
            ("change", "verb", "/tʃeɪndʒ/", ["менять", "изменять"], "To make or become different.", "Things will change soon.", "Скоро всё изменится."),
        ],
    },
    {
        "slug": "cefr-b1-intermediate",
        "title": "B1 • Intermediate Core",
        "description": "Многозначные слова, абстрактные понятия и уверенное общение",
        "target_level": "B1",
        "words": [
            ("mind", "noun", "/maɪnd/", ["разум", "ум"], "The element enabling conscious awareness.", "Keep an open mind.", "Сохраняй открытый разум."),
            ("sound", "adjective", "/saʊnd/", ["здравый", "надежный"], "Showing good judgment or condition.", "That was a sound decision.", "Это было здравое решение."),
            ("lead", "verb", "/liːd/", ["вести", "руководить"], "To show the way or be in charge.", "She leads a large team.", "Она руководит большой командой."),
            ("set", "verb", "/sɛt/", ["устанавливать", "задавать"], "To put in a specified state.", "Set a goal for yourself.", "Поставь себе цель."),
        ],
    },
    {
        "slug": "cefr-b2-upper-intermediate",
        "title": "B2 • Upper-Intermediate",
        "description": "Словарный запас для дискуссий, аргументации и работы",
        "target_level": "B2",
        "words": [
            ("acquire", "verb", "/əˈkwaɪər/", ["приобретать", "овладевать"], "To buy or gain possession of something.", "He acquired valuable skills.", "Он овладел ценными навыками."),
            ("reliable", "adjective", "/rɪˈlaɪ.ə.bəl/", ["надежный", "достоверный"], "Consistently good in quality or performance.", "We need reliable data.", "Нам нужны достоверные данные."),
            ("crucial", "adjective", "/ˈkruː.ʃəl/", ["решающий", "ключевой"], "Decisive or critical in nature.", "This is a crucial moment for our project.", "Это решающий момент для нашего проекта."),
            ("maintain", "verb", "/meɪnˈteɪn/", ["поддерживать", "сохранять"], "To cause or enable a condition to continue.", "It is vital to maintain focus.", "Жизненно важно сохранять концентрацию."),
        ],
    },
    {
        "slug": "cefr-c1-advanced",
        "title": "C1 • Advanced Academic & Business",
        "description": "Богатая академическая и профессиональная идиоматика",
        "target_level": "C1",
        "words": [
            ("inevitable", "adjective", "/ɪnˈɛv.ɪ.tə.bəl/", ["неизбежный"], "Certain to happen; unavoidable.", "Technological change is inevitable.", "Технологические перемены неизбежны."),
            ("elaborate", "adjective", "/ɪˈlæb.ər.ət/", ["детализированный", "продуманный"], "Involving many carefully arranged parts.", "They devised an elaborate strategy.", "Они разработали продуманную стратегию."),
            ("perceive", "verb", "/pərˈsiːv/", ["воспринимать", "осознавать"], "To interpret or regard in a particular way.", "How do you perceive this feedback?", "Как вы воспринимаете этот отзыв?"),
            ("subtle", "adjective", "/ˈsʌt.əl/", ["тонкий", "едва уловимый"], "So delicate as to be difficult to analyze.", "There is a subtle distinction here.", "Здесь есть едва уловимое различие."),
        ],
    },
    {
        "slug": "cefr-c2-proficiency",
        "title": "C2 • Native Proficiency",
        "description": "Редкая, стилистически окрашенная и экспрессивная лексика",
        "target_level": "C2",
        "words": [
            ("ubiquitous", "adjective", "/juːˈbɪk.wɪ.təs/", ["вездесущий", "повсеместный"], "Present, appearing, or found everywhere.", "Smartphones have become ubiquitous.", "Смартфоны стали вездесущими."),
            ("quintessential", "adjective", "/ˌkwɪn.tɪˈsɛn.ʃəl/", ["наиболее типичный", "хрестоматийный"], "Representing the most perfect example.", "It was the quintessential British afternoon.", "Это был классический британский полдень."),
            ("ephemeral", "adjective", "/ɪˈfɛm.ər.əl/", ["мимолетный", "эфемерный"], "Lasting for a very short time.", "Fame is often fleeting and ephemeral.", "Слава часто быстротечна и эфемерна."),
            ("meticulous", "adjective", "/məˈtɪk.jə.ləs/", ["скрупулезный", "дотошный"], "Showing great attention to every detail.", "He did meticulous research on the topic.", "Он провел скрупулезное исследование этой темы."),
        ],
    },
]


async def seed_system_dictionaries() -> None:
    async with async_session_maker() as session:
        for pack in SYSTEM_PACKS:
            # 1. Проверяем или создаем системный словарь
            stmt = select(SystemDictionary).where(SystemDictionary.slug == pack["slug"])
            result = await session.execute(stmt)
            sys_dict = result.scalar_one_or_none()

            if not sys_dict:
                sys_dict = SystemDictionary(
                    slug=pack["slug"],
                    title=pack["title"],
                    description=pack["description"],
                    target_level=pack["target_level"],
                )
                session.add(sys_dict)
                await session.flush()
                logger.info("Created system dictionary [%s]: %s", pack["target_level"], pack["title"])
            else:
                sys_dict.title = pack["title"]
                sys_dict.description = pack["description"]
                sys_dict.target_level = pack["target_level"]

            # 2. Гарантируем наличие слов и привязываем их к системному словарю
            for lemma, pos, trans, ru_translations, def_en, ex_en, ex_ru in pack["words"]:
                word_stmt = select(Word).where(Word.lemma == lemma)
                word_res = await session.execute(word_stmt)
                word = word_res.scalar_one_or_none()

                if not word:
                    word = Word(lemma=lemma)
                    sense = WordSense(
                        part_of_speech=pos,
                        transcription=trans,
                        translations_ru=ru_translations,
                        definition_en=def_en,
                        example_en=ex_en,
                        example_ru=ex_ru,
                        synonyms=[],
                        order_index=0,
                    )
                    word.senses.append(sense)
                    session.add(word)
                    await session.flush()

                # Привязка к словарю
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

        await session.commit()
    logger.info("All system dictionaries (A1-C2) successfully seeded!")


if __name__ == "__main__":
    asyncio.run(seed_system_dictionaries())