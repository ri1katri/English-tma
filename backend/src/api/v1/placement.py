import uuid
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.database import get_db
from src.models.dictionary import SystemDictionary
from src.models.user import User

router = APIRouter(prefix="/placement", tags=["placement"])

TEST_QUESTIONS = [
    {
        "id": 1,
        "word": "apple",
        "level": "A1",
        "question": "Что означает «apple»?",
        "options": ["яблоко", "книга", "вода", "машина"],
        "correct": "яблоко",
    },
    {
        "id": 2,
        "word": "water",
        "level": "A1",
        "question": "Что означает «water»?",
        "options": ["вода", "ветер", "огонь", "город"],
        "correct": "вода",
    },
    {
        "id": 3,
        "word": "city",
        "level": "A2",
        "question": "Что означает «city»?",
        "options": ["город", "деревня", "страна", "дорога"],
        "correct": "город",
    },
    {
        "id": 4,
        "word": "run",
        "level": "A2",
        "question": "Что означает глагол «run»?",
        "options": ["бежать", "думать", "лежать", "строить"],
        "correct": "бежать",
    },
    {
        "id": 5,
        "word": "develop",
        "level": "B1",
        "question": "Значение слова «develop»:",
        "options": ["развивать", "разрушать", "ограничивать", "скрывать"],
        "correct": "развивать",
    },
    {
        "id": 6,
        "word": "opportunity",
        "level": "B1",
        "question": "Значение слова «opportunity»:",
        "options": ["возможность", "препятствие", "происшествие", "опасность"],
        "correct": "возможность",
    },
    {
        "id": 7,
        "word": "sophisticated",
        "level": "B2",
        "question": "Что означает «sophisticated»?",
        "options": ["утонченный, сложный", "примитивный", "устаревший", "случайный"],
        "correct": "утонченный, сложный",
    },
    {
        "id": 8,
        "word": "inevitable",
        "level": "B2",
        "question": "Значение «inevitable»:",
        "options": ["неизбежный", "маловероятный", "сомнительный", "временный"],
        "correct": "неизбежный",
    },
    {
        "id": 9,
        "word": "comprehensive",
        "level": "C1",
        "question": "Значение «comprehensive»:",
        "options": ["всесторонний, полный", "понятный", "узкий", "сжатый"],
        "correct": "всесторонний, полный",
    },
    {
        "id": 10,
        "word": "resilient",
        "level": "C1",
        "question": "Значение «resilient»:",
        "options": ["стойкий, жизнеспособный", "хрупкий", "пассивный", "жестокий"],
        "correct": "стойкий, жизнеспособный",
    },
    {
        "id": 11,
        "word": "ubiquitous",
        "level": "C2",
        "question": "Что означает «ubiquitous»?",
        "options": ["вездесущий", "уникальный", "скрытный", "забытый"],
        "correct": "вездесущий",
    },
    {
        "id": 12,
        "word": "ephemeral",
        "level": "C2",
        "question": "Что означает «ephemeral»?",
        "options": ["мимолетный, недолговечный", "вечный", "прочный", "иллюзорный"],
        "correct": "мимолетный, недолговечный",
    },
]


class PlacementQuestionItem(BaseModel):
    id: int
    word: str
    level: str
    question: str
    options: List[str]


class PlacementTestResponse(BaseModel):
    questions: List[PlacementQuestionItem]


class PlacementSubmitRequest(BaseModel):
    answers: Dict[int, str]


class PlacementSubmitResponse(BaseModel):
    score: int
    total: int
    cefr_level: str
    recommended_dictionary_id: Optional[uuid.UUID] = None
    recommended_dictionary_title: Optional[str] = None


@router.get("/test", response_model=PlacementTestResponse)
async def get_test():
    items = []
    for q in TEST_QUESTIONS:
        opts = list(q["options"])
        opts.append("Не знаю")
        items.append(
            PlacementQuestionItem(
                id=q["id"],
                word=q["word"],
                level=q["level"],
                question=q["question"],
                options=opts,
            )
        )
    return PlacementTestResponse(questions=items)


@router.post("/submit", response_model=PlacementSubmitResponse)
async def submit_test(
    payload: PlacementSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    score = 0
    total = len(TEST_QUESTIONS)
    answers = payload.answers

    for q in TEST_QUESTIONS:
        user_ans = answers.get(q["id"]) or answers.get(str(q["id"]))
        if user_ans and user_ans.strip().lower() == q["correct"].strip().lower():
            score += 1

    # Шкала CEFR
    if score <= 2:
        level = "A1"
    elif score <= 4:
        level = "A2"
    elif score <= 6:
        level = "B1"
    elif score <= 8:
        level = "B2"
    elif score <= 10:
        level = "C1"
    else:
        level = "C2"

    # Сохраняем в профиль пользователя
    current_user.cefr_level = level
    current_user.placement_score = score
    current_user.placement_completed_at = func.now()
    await db.commit()

    # Ищем подходящий системный словарь
    stmt = (
        select(SystemDictionary)
        .where(SystemDictionary.target_level == level)
        .limit(1)
    )
    res = await db.execute(stmt)
    recommended_dict = res.scalar_one_or_none()

    if not recommended_dict:
        stmt_fallback = select(SystemDictionary).limit(1)
        res_fallback = await db.execute(stmt_fallback)
        recommended_dict = res_fallback.scalar_one_or_none()

    return PlacementSubmitResponse(
        score=score,
        total=total,
        cefr_level=level,
        recommended_dictionary_id=recommended_dict.id if recommended_dict else None,
        recommended_dictionary_title=recommended_dict.title if recommended_dict else None,
    )