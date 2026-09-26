import uuid
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


ExerciseType = Literal[
    "multiple_choice",
    "letter_scramble",
    "missing_letters",
    "sentence_reorder",
]


class LearningCard(BaseModel):
    question_id: uuid.UUID
    exercise_type: ExerciseType
    prompt_main: str
    prompt_sub: Optional[str] = None
    target_answer: str
    tokens: List[str] = Field(default_factory=list)
    options: List[str] = Field(default_factory=list)


class LearningSessionResponse(BaseModel):
    cards: List[LearningCard]


class SubmitAnswerRequest(BaseModel):
    word_id: uuid.UUID
    is_correct: bool


class SubmitAnswerResponse(BaseModel):
    status: str = "ok"
    new_status: str
    streak_count: int
    