from pydantic import BaseModel


class DashboardStatsResponse(BaseModel):
    total_words_in_dicts: int
    words_new: int
    words_learning: int
    words_mastered: int