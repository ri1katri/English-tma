import random
import re
import string
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.deps import get_current_user
from src.database import get_db
from src.models.dictionary import UserDictionary, UserDictionaryWord
from src.models.progress import UserWordProgress
from src.models.user import User
from src.models.word import Word
from src.schemas.learning import (
    LearningCard,
    LearningSessionResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)

router = APIRouter(prefix="/learning", tags=["learning"])


def _clean_tokens(sentence: str) -> List[str]:
    cleaned = re.sub(r"[^\w\s]", "", sentence)
    return [t for t in cleaned.split() if t]


@router.get("/session", response_model=LearningSessionResponse)
async def get_learning_session(
    dictionary_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(6, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    selected_words: List[Word] = []

    if dictionary_id:
        dict_stmt = select(UserDictionary).where(
            UserDictionary.id == dictionary_id,
            UserDictionary.user_id == current_user.id,
        )
        dict_res = await db.execute(dict_stmt)
        if not dict_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Словарь не найден",
            )

        words_stmt = (
            select(Word)
            .join(UserDictionaryWord, UserDictionaryWord.word_id == Word.id)
            .options(selectinload(Word.senses))
            .where(UserDictionaryWord.user_dictionary_id == dictionary_id)
        )
        words_res = await db.execute(words_stmt)
        dict_words = list(words_res.scalars().all())
        random.shuffle(dict_words)
        selected_words.extend(dict_words[:limit])
    else:
        prog_stmt = (
            select(Word)
            .join(UserWordProgress, UserWordProgress.word_id == Word.id)
            .options(selectinload(Word.senses))
            .where(
                UserWordProgress.user_id == current_user.id,
                UserWordProgress.status.in_(["learning", "new"]),
            )
            .order_by(UserWordProgress.streak_count.asc(), func.random())
            .limit(limit)
        )
        prog_res = await db.execute(prog_stmt)
        selected_words.extend(prog_res.scalars().all())

    if len(selected_words) < limit:
        needed = limit - len(selected_words)
        exclude_ids = [w.id for w in selected_words]
        fallback_stmt = (
            select(Word)
            .options(selectinload(Word.senses))
            .where(Word.id.not_in(exclude_ids) if exclude_ids else True)
            .order_by(func.random())
            .limit(needed)
        )
        fallback_res = await db.execute(fallback_stmt)
        selected_words.extend(fallback_res.scalars().all())

    if not selected_words:
        return LearningSessionResponse(cards=[])

    all_words_stmt = select(Word).options(selectinload(Word.senses)).limit(100)
    all_words_res = await db.execute(all_words_stmt)
    pool_words = list(all_words_res.scalars().all())

    cards: List[LearningCard] = []
    exercise_types = [
        "multiple_choice",
        "letter_scramble",
        "missing_letters",
        "sentence_reorder",
    ]

    for word in selected_words:
        sense = word.senses[0] if word.senses else None
        if not sense:
            continue

        chosen_type = random.choice(exercise_types)
        if chosen_type == "sentence_reorder" and not sense.example_en:
            chosen_type = random.choice(["multiple_choice", "letter_scramble", "missing_letters"])

        if chosen_type == "multiple_choice":
            correct_trans = sense.translations_ru[0] if sense.translations_ru else word.lemma
            distractor_pool = [
                pw.senses[0].translations_ru[0]
                for pw in pool_words
                if pw.id != word.id and pw.senses and pw.senses[0].translations_ru
            ]
            sampled = random.sample(distractor_pool, min(3, len(distractor_pool)))
            options = list(set([correct_trans] + sampled))
            while len(options) < 4:
                options.append(f"Вариант {len(options) + 1}")
            random.shuffle(options)

            cards.append(
                LearningCard(
                    question_id=word.id,
                    exercise_type="multiple_choice",
                    prompt_main=word.lemma,
                    prompt_sub=f"[{sense.transcription}] • {sense.part_of_speech}" if sense.transcription else sense.part_of_speech,
                    target_answer=correct_trans,
                    options=options,
                    tokens=[],
                )
            )

        elif chosen_type == "letter_scramble":
            word_letters = list(word.lemma.lower())
            extra_count = 2 if len(word_letters) <= 6 else 1
            distractors = [random.choice(string.ascii_lowercase) for _ in range(extra_count)]
            all_letters = word_letters + distractors
            random.shuffle(all_letters)

            cards.append(
                LearningCard(
                    question_id=word.id,
                    exercise_type="letter_scramble",
                    prompt_main=sense.translations_ru[0] if sense.translations_ru else word.lemma,
                    prompt_sub="Соберите слово из предложенных букв",
                    target_answer=word.lemma.lower(),
                    tokens=all_letters,
                    options=[],
                )
            )

        elif chosen_type == "missing_letters":
            w = word.lemma.lower()
            if len(w) <= 3:
                mask_indices = [len(w) // 2]
            else:
                num_blanks = min(2, len(w) - 2)
                mask_indices = sorted(random.sample(range(1, len(w) - 1), num_blanks))

            masked_word = "".join(
                "_" if i in mask_indices else char for i, char in enumerate(w)
            )
            correct_letters = [w[i] for i in mask_indices]
            extra_letters = [random.choice(string.ascii_lowercase) for _ in range(3)]
            tokens = correct_letters + extra_letters
            random.shuffle(tokens)

            cards.append(
                LearningCard(
                    question_id=word.id,
                    exercise_type="missing_letters",
                    prompt_main=masked_word,
                    prompt_sub=f"Перевод: {sense.translations_ru[0]}" if sense.translations_ru else "Восстановите пропущенные буквы",
                    target_answer=w,
                    tokens=tokens,
                    options=[],
                )
            )

        elif chosen_type == "sentence_reorder":
            sentence = sense.example_en.strip()
            tokens = _clean_tokens(sentence)
            shuffled_tokens = tokens.copy()
            random.shuffle(shuffled_tokens)

            cards.append(
                LearningCard(
                    question_id=word.id,
                    exercise_type="sentence_reorder",
                    prompt_main=sense.example_ru if sense.example_ru else "Соберите предложение",
                    prompt_sub="Порядок слов на английском языке",
                    target_answer=" ".join(tokens),
                    tokens=shuffled_tokens,
                    options=[],
                )
            )

    return LearningSessionResponse(cards=cards)


@router.post("/submit-answer", response_model=SubmitAnswerResponse)
async def submit_answer(
    payload: SubmitAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(UserWordProgress).where(
        UserWordProgress.user_id == current_user.id,
        UserWordProgress.word_id == payload.word_id,
    )
    res = await db.execute(stmt)
    progress = res.scalar_one_or_none()

    if not progress:
        progress = UserWordProgress(
            user_id=current_user.id,
            word_id=payload.word_id,
            status="learning",
        )
        db.add(progress)

    progress.last_reviewed_at = func.now()
    progress.updated_at = func.now()

    if payload.is_correct:
        progress.correct_count += 1
        progress.streak_count += 1
        if progress.streak_count >= 4:
            progress.status = "mastered"
        else:
            progress.status = "learning"
    else:
        progress.incorrect_count += 1
        progress.streak_count = 0
        progress.status = "learning"

    await db.commit()
    await db.refresh(progress)

    return SubmitAnswerResponse(
        status="ok",
        new_status=progress.status,
        streak_count=progress.streak_count,
    )