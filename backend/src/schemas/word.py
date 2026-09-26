import uuid
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class WordSenseResponse(BaseModel):
    id: uuid.UUID
    part_of_speech: str
    transcription: Optional[str] = None
    translations_ru: List[str] = Field(default_factory=list)
    definition_en: str
    example_en: Optional[str] = None
    example_ru: Optional[str] = None
    synonyms: List[str] = Field(default_factory=list)
    order_index: int

    model_config = ConfigDict(from_attributes=True)


class WordSearchResponse(BaseModel):
    id: uuid.UUID
    word: str
    senses: List[WordSenseResponse]

    model_config = ConfigDict(from_attributes=True)