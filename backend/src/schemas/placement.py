import uuid
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class PlacementQuestion(BaseModel):
    id: int
    level: str
    word: str
    prompt: str
    options: List[str]


class PlacementTestResponse(BaseModel):
    questions: List[PlacementQuestion]


class PlacementAnswerItem(BaseModel):
    question_id: int
    selected_option: str


class PlacementSubmitRequest(BaseModel):
    answers: List[PlacementAnswerItem]


class PlacementResultResponse(BaseModel):
    score: int
    total: int
    cefr_level: str
    level_title: str
    description: str
    recommended_dictionary_id: Optional[uuid.UUID] = None

    model_config = ConfigDict(from_attributes=True)