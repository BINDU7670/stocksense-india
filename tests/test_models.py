from __future__ import annotations

from datetime import datetime, timezone

from collectors.models import FullStockData, FundamentalsData, NewsItem, PriceData, SocialPost


def test_full_stock_data_serializes_with_nested_models() -> None:
    payload = FullStockData(
        ticker="RELIANCE",
        resolved_symbol="RELIANCE.NS",
        current_price=2950.0,
        price_history=[
            PriceData(
                symbol="RELIANCE.NS",
                exchange="NS",
                timestamp=datetime(2026, 4, 1, tzinfo=timezone.utc),
                open=2900.0,
                high=2960.0,
                low=2895.0,
                close=2950.0,
                volume=1000,
                current_price=2950.0,
            )
        ],
        fundamentals=FundamentalsData(
            ticker="RELIANCE",
            pe_ratio=24.5,
            pb_ratio=3.2,
            roe=16.0,
            roce=18.0,
            debt_to_equity=0.4,
            sales_growth=12.0,
            profit_growth=14.0,
            source_url="https://www.screener.in/company/RELIANCE/consolidated/",
        ),
        news=[
            NewsItem(
                source="Moneycontrol",
                title="Reliance eyes growth",
                url="https://example.com/reliance-news",
                published_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
                summary="Growth remains solid.",
                content="Growth remains solid and outlook is constructive.",
            )
        ],
        social_posts=[
            SocialPost(
                platform="X",
                author="@analyst",
                published_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
                content="Looks constructive.",
                url="https://x.com/reliance",
                sentiment_hint=0.2,
            )
        ],
    )

    reparsed = FullStockData.model_validate_json(payload.model_dump_json())
    assert reparsed.ticker == "RELIANCE"
    assert reparsed.fundamentals is not None
    assert reparsed.price_history[0].exchange == "NS"
