import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict


class TelegramAuthRequest(BaseModel):
    init_data: str


class UserResponse(BaseModel):
    id: uuid.UUID
    telegram_id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)