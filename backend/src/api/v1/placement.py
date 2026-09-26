from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.database import get_db
from src.models.dictionary import SystemDictionary
from src.models.user import User
from src.schemas.placement import (
    PlacementQuestion,
    PlacementResultResponse,
    PlacementSubmitRequest,
    PlacementTestResponse,
)

router = APIRouter(prefix="/placement", tags=["placement"])

# 12 вопросов нарастающей сложности (по 2 на каждый уровень A1-C2)
PLACEMENT_QUESTIONS = [
    # A1
    {
        "id": 1,
        "level": "A1",
        "word": "apple",
        "prompt": "Выберите правильный перевод слова «apple»:",
        "options": ["яблоко", "апельсин", "груша", "банан"],
        "correct": "яблоко",
    },
    {
        "id": 2,
        "level": "A1",
        "word": "water",
        "prompt": "Выберите правильный перевод слова «water»:",
        "options": ["вода", "молоко", "сок", "чай"],
        "correct": "вода",
    },
    # A2
    {
        "id": 3,
        "level": "A2",
        "word": "watch",
        "prompt": "Что означает глагол «to watch» в предложении: We watch films together?",
        "options": ["смотреть", "покупать", "слушать", "чинить"],
        "correct": "смотреть",
    },
    {
        "id": 4,
        "level": "A2",
        "word": "travel",
        "prompt": "Выберите перевод слова «travel»:",
        "options": ["путешествовать", "работать", "отдыхать", "готовиться"],
        "correct": "путешествовать",
    },
    # B1
    {
        "id": 5,
        "level": "B1",
        "word": "sound decision",
        "prompt": "Что означает «sound» во фразе «a sound decision»?",
        "options": ["здравое, взвешенное", "громкое", "быстрое", "ошибочное"],
        "correct": "здравое, взвешенное",
    },
    {
        "id": 6,
        "level": "B1",
        "word": "mind",
        "prompt": "Что означает фраза «keep in mind»?",
        "options": ["помнить, иметь в виду", "забыть", "сомневаться", "спорить"],
        "correct": "помнить, иметь в виду",
    },
    # B2
    {
        "id": 7,
        "level": "B2",
        "word": "crucial",
        "prompt": "Выберите синоним слова «crucial»:",
        "options": ["extremely important (решающий)", "boring", "useless", "cheap"],
        "correct": "extremely important (решающий)",
    },
    {
        "id": 8,
        "level": "B2",
        "word": "acquire",
        "prompt": "Выберите наиболее точный перевод слова «acquire»:",
        "options": ["овладевать, приобретать", "тратить", "терять", "требовать"],
        "correct": "овладевать, приобретать",
    },
    # C1
    {
        "id": 9,
        "level": "C1",
        "word": "inevitable",
        "prompt": "Что означает слово «inevitable»?",
        "options": ["неизбежный, неотвратимый", "вероятный", "необычный", "случайный"],
        "correct": "неизбежный, неотвратимый",
    },
    {
        "id": 10,
        "level": "C1",
        "word": "subtle",
        "prompt": "Что означает «a subtle difference»?",
        "options": ["тонкое, едва уловимое различие", "огромная разница", "явная ошибка", "странный случай"],
        "correct": "тонкое, едва уловимое различие",
    },
    # C2
    {
        "id": 11,
        "level": "C2",
        "word": "ubiquitous",
        "prompt": "Выберите определение слова «ubiquitous»:",
        "options": ["present everywhere (повсеместный)", "unique and rare", "dangerous", "ancient"],
        "correct": "present everywhere (повсеместный)",
    },
    {
        "id": 12,
        "level": "C2",
        "word": "ephemeral",
        "prompt": "Что означает прилагательное «ephemeral»?",
        "options": ["мимолетный, недолговечный", "вечный", "прочный", "иллюзорный"],
        "correct": "мимолетный, недолговечный",
    },
]


@router.get("/test", response_model=PlacementTestResponse)
async def get_placement_test():
    questions = []
    for q in PLACEMENT_QUESTIONS:
        opts = list(q["options"])
        opts.append("Не знаю")
        questions.append(
            PlacementQuestion(
                id=q["id"],
                level=q["level"],
                word=q["word"],
                prompt=q["prompt"],
                options=opts,
            )
        )
    return PlacementTestResponse(questions=questions)


@router.post("/submit", response_model=PlacementResultResponse)
async def submit_placement_test(
    payload: PlacementSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_answers = {a.question_id: a.selected_option for a in payload.answers}

    score = 0
    for q in PLACEMENT_QUESTIONS:
        if user_answers.get(q["id"]) == q["correct"]:
            score += 1

    # Шкала оценки
    if score <= 2:
        cefr = "A1"
        title = "A1 • Beginner"
        desc = "Вы в начале пути! Рекомендуем начать с базовой повседневной лексики."
    elif score <= 4:
        cefr = "A2"
        title = "A2 • Elementary"
        desc = "Хорошая база! Изучайте фразовые глаголы и действия."
    elif score <= 6:
        cefr = "B1"
        title = "B1 • Intermediate"
        desc = "Уверенная база. Время обогатить речь многозначными словами и идиомами."
    elif score <= 8:
        cefr = "B2"
        title = "B2 • Upper-Intermediate"
        desc = "Отличный уровень! Тренируйте абстрактные понятия и деловую лексику."
    elif score <= 10:
        cefr = "C1"
        title = "C1 • Advanced"
        desc = "Продвинутый уровень! Вы готовы к чтению сложных текстов и дискуссиям."
    else:
        cefr = "C2"
        title = "C2 • Proficiency"
        desc = "Блестяще! Вы владеете языком на уровне носителя."

    # Сохранение результата в профиле пользователя
    current_user.cefr_level = cefr
    current_user.placement_score = score
    current_user.placement_completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(current_user)

    # Поиск рекомендованного системного словаря для этого уровня
    dict_stmt = select(SystemDictionary).where(SystemDictionary.target_level == cefr)
    dict_res = await db.execute(dict_stmt)
    rec_dict = dict_res.scalars().first()

    return PlacementResultResponse(
        score=score,
        total=len(PLACEMENT_QUESTIONS),
        cefr_level=cefr,
        level_title=title,
        description=desc,
        recommended_dictionary_id=rec_dict.id if rec_dict else None,
    )