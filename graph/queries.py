from __future__ import annotations

from collectors.models import NewsItem, PriceData
from graph.db import GraphDatabase


def get_price_history(db: GraphDatabase, ticker: str) -> list[PriceData]:
    return db.get_price_history(ticker)


def get_news(db: GraphDatabase, ticker: str, limit: int | None = None) -> list[NewsItem]:
    return db.get_news(ticker, limit=limit)


def get_sentiment(db: GraphDatabase, ticker: str) -> dict[str, float | int | str]:
    return db.get_sentiment(ticker)
