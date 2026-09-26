import uuid
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict


class WordProgressUpdateRequest(BaseModel):
    status: Literal["new", "learning", "mastered"]


class WordProgressResponse(BaseModel):
    word_id: uuid.UUID
    status: str
    correct_count: int = 0
    incorrect_count: int = 0
    streak_count: int = 0
    last_reviewed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)