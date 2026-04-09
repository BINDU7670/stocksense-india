from __future__ import annotations

import json
from pathlib import Path

from collectors.models import FullStockData, NewsItem, PriceData
from utils.settings import GRAPH_DIR, ensure_directories


class GraphDatabase:
    """A lightweight persisted graph simulation for local development."""

    def __init__(self, store_path: Path | None = None) -> None:
        ensure_directories()
        self.store_path = store_path or (GRAPH_DIR / "graph_store.json")
        if not self.store_path.exists():
            self.store_path.write_text("{}", encoding="utf-8")

    def _load(self) -> dict[str, dict]:
        return json.loads(self.store_path.read_text(encoding="utf-8"))

    def _save(self, payload: dict[str, dict]) -> None:
        self.store_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def ingest_stock_data(self, stock_data: FullStockData) -> None:
        payload = self._load()
        payload[stock_data.ticker.upper()] = stock_data.model_dump(mode="json")
        self._save(payload)

    def get_stock(self, ticker: str) -> FullStockData | None:
        payload = self._load()
        document = payload.get(ticker.upper())
        return FullStockData.model_validate(document) if document else None

    def get_price_history(self, ticker: str) -> list[PriceData]:
        stock = self.get_stock(ticker)
        return stock.price_history if stock else []

    def get_news(self, ticker: str, limit: int | None = None) -> list[NewsItem]:
        stock = self.get_stock(ticker)
        news = stock.news if stock else []
        return news[:limit] if limit is not None else news

    def get_sentiment(self, ticker: str) -> dict[str, float | int | str]:
        stock = self.get_stock(ticker)
        if stock is None:
            return {
                "ticker": ticker.upper(),
                "news_sentiment": 0.0,
                "social_sentiment": 0.0,
                "combined_sentiment": 0.0,
                "news_count": 0,
                "social_count": 0,
            }

        social_scores = [post.sentiment_hint for post in stock.social_posts if post.sentiment_hint is not None]
        news_scores = [self._estimate_text_sentiment(item.summary + " " + item.content) for item in stock.news]

        news_sentiment = sum(news_scores) / len(news_scores) if news_scores else 0.0
        social_sentiment = sum(social_scores) / len(social_scores) if social_scores else 0.0
        total_count = len(news_scores) + len(social_scores)
        combined = (
            ((news_sentiment * len(news_scores)) + (social_sentiment * len(social_scores))) / total_count
            if total_count
            else 0.0
        )

        return {
            "ticker": stock.ticker,
            "news_sentiment": round(news_sentiment, 3),
            "social_sentiment": round(social_sentiment, 3),
            "combined_sentiment": round(combined, 3),
            "news_count": len(news_scores),
            "social_count": len(social_scores),
        }

    @staticmethod
    def _estimate_text_sentiment(text: str) -> float:
        lowered = text.lower()
        positive_terms = ("beat", "growth", "bullish", "strong", "outperform", "upside", "expansion")
        negative_terms = ("fall", "probe", "debt", "bearish", "weak", "slump", "downgrade", "risk")

        positive_hits = sum(term in lowered for term in positive_terms)
        negative_hits = sum(term in lowered for term in negative_terms)
        total = positive_hits + negative_hits
        if total == 0:
            return 0.0
        return (positive_hits - negative_hits) / total
