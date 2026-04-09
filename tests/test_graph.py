from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from collectors.models import FullStockData, NewsItem, PriceData, SocialPost
from graph.db import GraphDatabase
from graph.queries import get_news, get_price_history, get_sentiment


def _sample_stock_data() -> FullStockData:
    return FullStockData(
        ticker="INFY",
        resolved_symbol="INFY.NS",
        current_price=1500.0,
        price_history=[
            PriceData(
                symbol="INFY.NS",
                exchange="NS",
                timestamp=datetime(2026, 4, 1, tzinfo=timezone.utc),
                open=1490.0,
                high=1510.0,
                low=1480.0,
                close=1500.0,
                volume=500,
                current_price=1500.0,
            )
        ],
        news=[
            NewsItem(
                source="ET Markets",
                title="Infosys growth remains strong",
                url="https://example.com/infy-news",
                published_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
                summary="Strong demand backdrop continues.",
                content="Strong growth and expansion support the outlook.",
            )
        ],
        social_posts=[
            SocialPost(
                platform="Reddit",
                author="u/test",
                published_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
                content="Bullish setup.",
                url="https://reddit.com/r/test",
                sentiment_hint=0.4,
            )
        ],
    )


def test_graph_database_persists_and_queries(tmp_path: Path) -> None:
    db = GraphDatabase(store_path=tmp_path / "graph_store.json")
    db.ingest_stock_data(_sample_stock_data())

    history = get_price_history(db, "INFY")
    news = get_news(db, "INFY")
    sentiment = get_sentiment(db, "INFY")

    assert len(history) == 1
    assert len(news) == 1
    assert sentiment["combined_sentiment"] > 0
