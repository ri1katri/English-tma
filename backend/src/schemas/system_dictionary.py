import uuid
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from src.schemas.word import WordSearchResponse


class SystemDictionarySummaryResponse(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    description: Optional[str] = None
    target_level: Optional[str] = None
    words_count: int

    model_config = ConfigDict(from_attributes=True)


class SystemDictionaryDetailResponse(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    description: Optional[str] = None
    target_level: Optional[str] = None
    words: List[WordSearchResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)