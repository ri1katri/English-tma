import asyncio
from sqlalchemy import select
from src.database import async_session_maker
from src.models.dictionary import SystemDictionary, SystemDictionaryWord
from src.models.word import Word, WordSense

PACKS = [
    {
        "slug": "pack-a1",
        "title": "A1 • Первые шаги",
        "description": "Базовая лексика для начинающих: еда, дом, простые действия.",
        "target_level": "A1",
        "words": [
            ("apple", "noun", "/ˈæp.əl/", ["яблоко"], "A round fruit with red or green skin.", "She eats an apple.", "Она ест яблоко."),
            ("water", "noun", "/ˈwɔː.tər/", ["вода"], "A clear liquid essential for life.", "Drink pure water.", "Пейте чистую воду."),
            ("book", "noun", "/bʊk/", ["книга"], "A set of printed pages bound together.", "I read a book.", "Я читаю книгу."),
            ("light", "noun", "/laɪt/", ["свет"], "The natural agent that makes things visible.", "Turn on the light.", "Включите свет."),
            ("day", "noun", "/deɪ/", ["день"], "Each of the twenty-four-hour periods.", "Have a nice day.", "Хорошего дня."),
            ("friend", "noun", "/frend/", ["друг"], "A person with whom one has a bond.", "He is my best friend.", "Он мой лучший друг."),
        ],
    },
    {
        "slug": "pack-b1",
        "title": "B1 • Разговорный английский",
        "description": "Уверенное общение: действия, планы, работа и социум.",
        "target_level": "B1",
        "words": [
            ("run", "verb", "/rʌn/", ["бежать", "бегать"], "To move fast on foot.", "Run every morning.", "Бегай каждое утро."),
            ("set", "verb", "/set/", ["устанавливать"], "To put in a specified place.", "Set the alarm clock.", "Установи будильник."),
            ("develop", "verb", "/dɪˈvel.əp/", ["развивать"], "To grow or cause to grow.", "Develop your skills.", "Развивай свои навыки."),
            ("opportunity", "noun", "/ˌɒp.əˈtjuː.nə.ti/", ["возможность"], "A set of circumstances that makes it possible.", "Great opportunity.", "Отличная возможность."),
            ("community", "noun", "/kəˈmjuː.nə.ti/", ["сообщество"], "A group of people living in the same place.", "Join our community.", "Присоединяйся к сообществу."),
            ("decision", "noun", "/dɪˈsɪʒ.ən/", ["решение"], "A conclusion reached after consideration.", "Make a decision.", "Прими решение."),
        ],
    },
    {
        "slug": "pack-c1",
        "title": "C1 • Продвинутый уровень",
        "description": "Академическая и деловая лексика для свободного владения.",
        "target_level": "C1",
        "words": [
            ("comprehensive", "adjective", "/ˌkɒm.prɪˈhen.sɪv/", ["всесторонний", "полный"], "Including or dealing with all elements.", "A comprehensive guide.", "Полное руководство."),
            ("resilient", "adjective", "/rɪˈzɪl.jənt/", ["стойкий", "жизнеспособный"], "Able to withstand difficulties.", "Resilient economy.", "Стойкая экономика."),
            ("sophisticated", "adjective", "/səˈfɪs.tɪ.keɪ.tɪd/", ["утонченный", "сложный"], "Having great complexity.", "Sophisticated technology.", "Сложная технология."),
            ("inevitable", "adjective", "/ɪnˈev.ɪ.tə.bəl/", ["неизбежный"], "Certain to happen; unavoidable.", "Change is inevitable.", "Перемены неизбежны."),
            ("ubiquitous", "adjective", "/juːˈbɪk.wɪ.təs/", ["вездесущий"], "Present or found everywhere.", "Smartphones are ubiquitous.", "Смартфоны вездесущи."),
            ("ephemeral", "adjective", "/ɪˈfem.ər.əl/", ["мимолетный"], "Lasting for a very short time.", "Ephemeral moment.", "Мимолетный момент."),
        ],
    },
]


async def seed():
    async with async_session_maker() as session:
        for pack in PACKS:
            stmt = select(SystemDictionary).where(SystemDictionary.slug == pack["slug"])
            res = await session.execute(stmt)
            sys_dict = res.scalar_one_or_none()

            if not sys_dict:
                sys_dict = SystemDictionary(
                    slug=pack["slug"],
                    title=pack["title"],
                    description=pack["description"],
                    target_level=pack["target_level"],
                )
                session.add(sys_dict)
                await session.flush()

            for lemma, pos, ipa, tr_ru, def_en, ex_en, ex_ru in pack["words"]:
                w_stmt = select(Word).where(Word.lemma == lemma)
                w_res = await session.execute(w_stmt)
                word = w_res.scalar_one_or_none()

                if not word:
                    word = Word(lemma=lemma)
                    session.add(word)
                    await session.flush()

                    sense = WordSense(
                        word_id=word.id,
                        part_of_speech=pos,
                        transcription=ipa,
                        translations_ru=tr_ru,
                        definition_en=def_en,
                        example_en=ex_en,
                        example_ru=ex_ru,
                        synonyms=[],
                        order_index=0,
                    )
                    session.add(sense)
                    await session.flush()

                # Связываем слово со словарём
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
        print("Системные словари успешно наполнены словами!")


if __name__ == "__main__":
    asyncio.run(seed())