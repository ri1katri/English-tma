from src.schemas.auth import TelegramAuthRequest, UserResponse
from src.schemas.dictionary import (
    DictionaryAddWordRequest,
    DictionaryCreateRequest,
    DictionaryDetailResponse,
    DictionarySummaryResponse,
)
from src.schemas.learning import (
    LearningCard,
    LearningSessionResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from src.schemas.progress import WordProgressResponse, WordProgressUpdateRequest
from src.schemas.system_dictionary import (
    SystemDictionaryDetailResponse,
    SystemDictionarySummaryResponse,
)
from src.schemas.user import DashboardStatsResponse
from src.schemas.word import WordSearchResponse, WordSenseResponse

__all__ = [
    "TelegramAuthRequest",
    "UserResponse",
    "WordSearchResponse",
    "WordSenseResponse",
    "DictionaryCreateRequest",
    "DictionaryAddWordRequest",
    "DictionarySummaryResponse",
    "DictionaryDetailResponse",
    "SystemDictionarySummaryResponse",
    "SystemDictionaryDetailResponse",
    "WordProgressUpdateRequest",
    "WordProgressResponse",
    "DashboardStatsResponse",
    "LearningCard",
    "LearningSessionResponse",
    "SubmitAnswerRequest",
    "SubmitAnswerResponse",
]