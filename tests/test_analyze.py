from __future__ import annotations

import json

import agents.analyze
from agents.analyze import RawStockAnalyzer
from utils.llm import LLMConfigurationError


def _write_raw_snapshot(tmp_path) -> None:
    payload = {
        "ticker": "RELIANCE",
        "fundamentals": {
            "ticker": "RELIANCE",
            "pe_ratio": 24.1,
            "roe": None,
            "debt_to_equity": 0.32,
            "sales_growth": 11.8,
            "profit_growth": 13.2,
            "source_url": "https://www.screener.in/company/RELIANCE/consolidated/"
        },
        "news": [
            {
                "source": "Moneycontrol",
                "title": "Reliance growth outlook remains strong",
                "url": "https://example.com/reliance-news",
                "published_at": "2026-04-09T05:00:00+00:00",
                "summary": None,
                "content": "Growth remains strong and expansion plans are on track."
            },
            {
                "source": None,
                "title": None,
                "url": None,
                "published_at": None,
                "summary": None,
                "content": None
            }
        ],
        "social_posts": None,
        "errors": None
    }
    (tmp_path / "RELIANCE.json").write_text(json.dumps(payload), encoding="utf-8")


def _raise_no_llm(*args: object, **kwargs: object) -> None:
    raise LLMConfigurationError("LLM disabled for test.")


def test_raw_stock_analyzer_handles_nulls_and_llm_response(tmp_path, monkeypatch) -> None:
    _write_raw_snapshot(tmp_path)

    monkeypatch.setattr(
        agents.analyze,
        "complete_json",
        lambda **kwargs: {
            "sentiment_summary": "Narrative is constructive.",
            "key_insights": ["Growth remains strong.", "Leverage is manageable."],
            "risks": ["Macro slowdown could hit demand."],
            "final_recommendation": "Buy",
        },
    )

    result = RawStockAnalyzer(raw_data_dir=tmp_path).analyze_ticker("reliance")

    assert result.ticker == "RELIANCE"
    assert result.final_recommendation == "Buy"
    assert result.key_insights[0] == "Growth remains strong."


def test_raw_stock_analyzer_falls_back_when_llm_is_unavailable(tmp_path, monkeypatch) -> None:
    _write_raw_snapshot(tmp_path)
    monkeypatch.setattr(agents.analyze, "complete_json", _raise_no_llm)

    result = RawStockAnalyzer(raw_data_dir=tmp_path).analyze_ticker("RELIANCE")

    assert result.ticker == "RELIANCE"
    assert result.final_recommendation in {"Buy", "Hold", "Sell"}
    assert result.sentiment_summary
