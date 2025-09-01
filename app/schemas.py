from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

class Overview(BaseModel):
    total_titles: int
    year_range: tuple[int, int] | None
    sum_global_sales: float | None
    avg_critic_score: float | None
    avg_user_score: float | None

class GameItem(BaseModel):
    name: str
    platform: Optional[str] = None
    genre: Optional[str] = None
    year: Optional[int] = None
    publisher: Optional[str] = None
    developer: Optional[str] = None
    rating: Optional[str] = None
    global_sales: Optional[float] = None
    na_sales: Optional[float] = None
    eu_sales: Optional[float] = None
    jp_sales: Optional[float] = None
    other_sales: Optional[float] = None
    critic_score: Optional[float] = None
    user_score: Optional[float] = None

class RankingResponse(BaseModel):
    metric: Literal["global_sales","na_sales","eu_sales","jp_sales","critic_score","user_score"]
    filters: dict[str, Any]
    total: int
    items: list[GameItem]
