from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class PriceData(BaseModel):
    symbol: str
    exchange: Literal["NS", "BO", "UNKNOWN"] = "UNKNOWN"
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    current_price: float | None = None
    currency: str = "INR"


class FundamentalsData(BaseModel):
    ticker: str
    pe_ratio: float | None = None
    pb_ratio: float | None = None
    roe: float | None = None
    roce: float | None = None
    debt_to_equity: float | None = None
    sales_growth: float | None = None
    profit_growth: float | None = None
    source_url: HttpUrl | None = None
    extracted_at: datetime = Field(default_factory=datetime.utcnow)


class NewsItem(BaseModel):
    source: str
    title: str
    url: HttpUrl
    published_at: datetime
    summary: str
    content: str


class SocialPost(BaseModel):
    platform: str
    author: str
    published_at: datetime
    content: str
    url: HttpUrl | None = None
    sentiment_hint: float | None = Field(default=None, ge=-1.0, le=1.0)


class FullStockData(BaseModel):
    ticker: str
    resolved_symbol: str | None = None
    current_price: float | None = None
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    price_history: list[PriceData] = Field(default_factory=list)
    fundamentals: FundamentalsData | None = None
    news: list[NewsItem] = Field(default_factory=list)
    social_posts: list[SocialPost] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
