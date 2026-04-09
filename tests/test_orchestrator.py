from __future__ import annotations

from datetime import datetime, timedelta, timezone

import agents.base
import agents.orchestrator
from agents.orchestrator import AnalysisOrchestrator
from collectors.models import FullStockData, FundamentalsData, NewsItem, PriceData, SocialPost
from utils.llm import LLMConfigurationError


def _sample_stock_data() -> FullStockData:
    base_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return FullStockData(
        ticker="TATAMOTORS",
        resolved_symbol="TATAMOTORS.NS",
        current_price=980.0,
        price_history=[
            PriceData(
                symbol="TATAMOTORS.NS",
                exchange="NS",
                timestamp=base_date + timedelta(days=day - 1),
                open=800.0 + day,
                high=805.0 + day,
                low=795.0 + day,
                close=810.0 + (day * 2),
                volume=10_000 + day,
                current_price=980.0,
            )
            for day in range(1, 61)
        ],
        fundamentals=FundamentalsData(
            ticker="TATAMOTORS",
            pe_ratio=18.0,
            pb_ratio=4.0,
            roe=17.0,
            roce=19.0,
            debt_to_equity=0.45,
            sales_growth=11.0,
            profit_growth=15.0,
            source_url="https://www.screener.in/company/TATAMOTORS/consolidated/",
        ),
        news=[
            NewsItem(
                source="Moneycontrol",
                title="Tata Motors growth outlook stays strong",
                url="https://example.com/tatamotors-news",
                published_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
                summary="Strong demand supports growth.",
                content="Strong expansion and growth keep sentiment constructive.",
            )
        ],
        social_posts=[
            SocialPost(
                platform="X",
                author="@tester",
                published_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
                content="Bullish setup.",
                url="https://x.com/tatamotors",
                sentiment_hint=0.3,
            )
        ],
    )


def _raise_no_llm(*args: object, **kwargs: object) -> None:
    raise LLMConfigurationError("LLM disabled for test.")


def test_orchestrator_fallback_builds_report(monkeypatch) -> None:
    monkeypatch.setattr(agents.base, "complete_json", _raise_no_llm)
    monkeypatch.setattr(agents.orchestrator, "complete_json", _raise_no_llm)

    report = AnalysisOrchestrator().analyze(_sample_stock_data())

    assert report.ticker == "TATAMOTORS"
    assert report.recommendation in {"Buy", "Accumulate", "Hold", "Reduce", "Avoid"}
    assert set(report.agent_outputs.keys()) == {"fundamental", "technical", "sentiment"}
