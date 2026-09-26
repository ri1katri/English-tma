import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from src.schemas.word import WordSearchResponse


class DictionaryCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    description: Optional[str] = Field(default=None, max_length=500)


class DictionaryAddWordRequest(BaseModel):
    word_id: uuid.UUID


class DictionarySummaryResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    words_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DictionaryDetailResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    created_at: datetime
    words: List[WordSearchResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)