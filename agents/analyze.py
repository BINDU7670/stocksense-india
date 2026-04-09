from __future__ import annotations

import argparse
import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from collectors.models import FundamentalsData, FullStockData, NewsItem, SocialPost
from utils.llm import LLMConfigurationError, LLMRequestError, complete_json
from utils.settings import RAW_DATA_DIR

LOGGER = logging.getLogger(__name__)
ANALYSIS_MODEL = "qwen/qwen3.6-plus:free"


class NewsDigest(BaseModel):
    source: str
    title: str
    published_at: str
    summary: str


class SocialDigest(BaseModel):
    platform: str
    author: str
    published_at: str
    content: str
    sentiment_hint: float | None = None


class AnalysisContext(BaseModel):
    ticker: str
    fundamentals: dict[str, float | str | None]
    social_posts: list[SocialDigest] = Field(default_factory=list)
    news: list[NewsDigest] = Field(default_factory=list)
    data_quality_notes: list[str] = Field(default_factory=list)


class StructuredAnalysis(BaseModel):
    ticker: str
    sentiment_summary: str
    key_insights: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    final_recommendation: Literal["Buy", "Hold", "Sell"]


class RawStockAnalyzer:
    def __init__(
        self,
        raw_data_dir: Path | None = None,
        model: str = ANALYSIS_MODEL,
    ) -> None:
        self.raw_data_dir = raw_data_dir or RAW_DATA_DIR
        self.model = model

    def analyze_ticker(self, ticker: str) -> StructuredAnalysis:
        stock_data = self.load_snapshot(ticker)
        context = self.extract_context(stock_data)
        return self._generate_analysis(context)

    def load_snapshot(self, ticker: str) -> FullStockData:
        normalized_ticker = ticker.upper().strip()
        snapshot_path = self.raw_data_dir / f"{normalized_ticker}.json"
        if not snapshot_path.exists():
            raise FileNotFoundError(f"Raw snapshot not found: {snapshot_path}")

        raw_payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        if not isinstance(raw_payload, dict):
            raise ValueError(f"Snapshot payload for {normalized_ticker} must be a JSON object.")

        return self._build_stock_data(normalized_ticker, raw_payload)

    def extract_context(self, stock_data: FullStockData) -> AnalysisContext:
        data_quality_notes = list(stock_data.errors)
        if stock_data.fundamentals is None:
            data_quality_notes.append("Fundamentals data is missing or incomplete.")
        if not stock_data.news:
            data_quality_notes.append("No recent news articles were available in the raw snapshot.")
        if not stock_data.social_posts:
            data_quality_notes.append("No social posts were available in the raw snapshot.")

        return AnalysisContext(
            ticker=stock_data.ticker,
            fundamentals=self._fundamentals_snapshot(stock_data.fundamentals),
            social_posts=[
                SocialDigest(
                    platform=post.platform,
                    author=post.author,
                    published_at=post.published_at.isoformat(),
                    content=self._truncate(post.content, 300),
                    sentiment_hint=post.sentiment_hint,
                )
                for post in stock_data.social_posts[:6]
            ],
            news=[
                NewsDigest(
                    source=item.source,
                    title=item.title,
                    published_at=item.published_at.isoformat(),
                    summary=self._truncate(item.summary or item.content, 400),
                )
                for item in stock_data.news[:6]
            ],
            data_quality_notes=data_quality_notes[:6],
        )

    def _generate_analysis(self, context: AnalysisContext) -> StructuredAnalysis:
        try:
            payload = complete_json(
                system_prompt=self._system_prompt(),
                user_prompt=self._user_prompt(context),
                temperature=0.15,
                max_tokens=900,
                model=self.model,
            )
            payload["ticker"] = context.ticker
            return StructuredAnalysis.model_validate(payload)
        except (LLMConfigurationError, LLMRequestError, ValueError) as exc:
            LOGGER.warning("Falling back to deterministic analysis for %s: %s", context.ticker, exc)
            return self._fallback_analysis(context)

    @staticmethod
    def _system_prompt() -> str:
        return (
            "You are a senior Indian equity research analyst. "
            "Return only valid JSON with the keys sentiment_summary, key_insights, risks, and "
            "final_recommendation. final_recommendation must be one of Buy, Hold, or Sell. "
            "Keep key_insights and risks concise, factual, and decision-oriented."
        )

    @staticmethod
    def _user_prompt(context: AnalysisContext) -> str:
        return (
            "Analyze the following raw stock snapshot summary and produce an investor-ready output.\n"
            f"{context.model_dump_json(indent=2)}"
        )

    def _fallback_analysis(self, context: AnalysisContext) -> StructuredAnalysis:
        social_scores = [item.sentiment_hint for item in context.social_posts if item.sentiment_hint is not None]
        social_score = sum(social_scores) / len(social_scores) if social_scores else 0.0
        news_score = self._estimate_news_sentiment(context.news)
        combined_score = round((social_score + news_score) / 2, 3)

        key_insights = self._build_key_insights(context, combined_score)
        risks = self._build_risks(context, combined_score)

        return StructuredAnalysis(
            ticker=context.ticker,
            sentiment_summary=(
                f"Market narrative is {'constructive' if combined_score > 0.15 else 'cautious' if combined_score < -0.15 else 'balanced'} "
                f"with combined sentiment at {combined_score:.2f} based on news and social signals."
            ),
            key_insights=key_insights,
            risks=risks,
            final_recommendation=self._recommendation_from_score(combined_score, context),
        )

    @staticmethod
    def _build_key_insights(context: AnalysisContext, combined_score: float) -> list[str]:
        insights: list[str] = []
        fundamentals = context.fundamentals

        if fundamentals.get("pe_ratio") is not None:
            insights.append(f"P/E stands at {fundamentals['pe_ratio']}, which shapes the valuation base.")
        if fundamentals.get("roe") is not None:
            insights.append(f"ROE is {fundamentals['roe']}%, giving a quick read on capital efficiency.")
        if fundamentals.get("sales_growth") is not None:
            insights.append(f"Sales growth is {fundamentals['sales_growth']}%, indicating revenue momentum.")
        if context.news:
            insights.append(f"Recent news flow is led by: {context.news[0].title}")
        if context.social_posts:
            insights.append(
                f"Social chatter is {'positive' if combined_score > 0.15 else 'mixed'} across {len(context.social_posts)} recent posts."
            )

        if not insights:
            insights.append("Available raw data is limited, so the current read is based on sparse signals.")
        return insights[:4]

    @staticmethod
    def _build_risks(context: AnalysisContext, combined_score: float) -> list[str]:
        risks: list[str] = []
        fundamentals = context.fundamentals

        debt_to_equity = fundamentals.get("debt_to_equity")
        if isinstance(debt_to_equity, (float, int)) and debt_to_equity >= 1:
            risks.append(f"Debt-to-equity at {debt_to_equity} suggests leverage could amplify downside risk.")

        profit_growth = fundamentals.get("profit_growth")
        if isinstance(profit_growth, (float, int)) and profit_growth < 5:
            risks.append("Profit growth is soft, which can pressure earnings expectations.")

        if combined_score < -0.15:
            risks.append("Current narrative sentiment is negative, raising the probability of near-term weakness.")

        risks.extend(context.data_quality_notes[:2])
        deduplicated_risks = list(dict.fromkeys(risks))
        if not deduplicated_risks:
            deduplicated_risks.append("Macro volatility and sector-specific execution risk can alter the setup quickly.")
        return deduplicated_risks[:4]

    @staticmethod
    def _recommendation_from_score(
        combined_score: float,
        context: AnalysisContext,
    ) -> Literal["Buy", "Hold", "Sell"]:
        debt_to_equity = context.fundamentals.get("debt_to_equity")
        if combined_score >= 0.2 and (
            not isinstance(debt_to_equity, (float, int)) or debt_to_equity < 1
        ):
            return "Buy"
        if combined_score <= -0.2:
            return "Sell"
        return "Hold"

    @staticmethod
    def _estimate_news_sentiment(news_items: list[NewsDigest]) -> float:
        positive_terms = ("growth", "strong", "beat", "upside", "expansion", "profit")
        negative_terms = ("debt", "probe", "weak", "downgrade", "fall", "risk")

        combined_text = " ".join(f"{item.title} {item.summary}" for item in news_items).lower()
        positive_hits = sum(term in combined_text for term in positive_terms)
        negative_hits = sum(term in combined_text for term in negative_terms)
        total_hits = positive_hits + negative_hits
        if total_hits == 0:
            return 0.0
        return round((positive_hits - negative_hits) / total_hits, 3)

    def _build_stock_data(self, ticker: str, raw_payload: dict[str, Any]) -> FullStockData:
        collected_at = self._safe_datetime(raw_payload.get("collected_at"))
        fundamentals = self._normalize_fundamentals(raw_payload.get("fundamentals"), ticker)
        news_items = self._normalize_news_items(raw_payload.get("news"), collected_at)
        social_posts = self._normalize_social_posts(raw_payload.get("social_posts"), collected_at)

        return FullStockData(
            ticker=self._safe_string(raw_payload.get("ticker"), ticker),
            resolved_symbol=self._safe_optional_string(raw_payload.get("resolved_symbol")),
            current_price=self._safe_float(raw_payload.get("current_price")),
            collected_at=collected_at,
            fundamentals=fundamentals,
            news=news_items,
            social_posts=social_posts,
            errors=self._normalize_string_list(raw_payload.get("errors")),
        )

    def _normalize_fundamentals(
        self,
        payload: Any,
        ticker: str,
    ) -> FundamentalsData | None:
        if not isinstance(payload, dict):
            return None

        source_url = self._safe_optional_string(payload.get("source_url"))
        fundamentals_payload: dict[str, Any] = {
            "ticker": self._safe_string(payload.get("ticker"), ticker),
            "pe_ratio": self._safe_float(payload.get("pe_ratio")),
            "pb_ratio": self._safe_float(payload.get("pb_ratio")),
            "roe": self._safe_float(payload.get("roe")),
            "roce": self._safe_float(payload.get("roce")),
            "debt_to_equity": self._safe_float(payload.get("debt_to_equity")),
            "sales_growth": self._safe_float(payload.get("sales_growth")),
            "profit_growth": self._safe_float(payload.get("profit_growth")),
            "extracted_at": self._safe_datetime(payload.get("extracted_at")),
        }
        if source_url:
            fundamentals_payload["source_url"] = source_url

        try:
            return FundamentalsData.model_validate(fundamentals_payload)
        except ValueError:
            LOGGER.warning("Failed to normalize fundamentals for %s", ticker)
            return None

    def _normalize_news_items(self, payload: Any, fallback_time: datetime) -> list[NewsItem]:
        if not isinstance(payload, list):
            return []

        items: list[NewsItem] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            url = self._safe_optional_string(entry.get("url"))
            title = self._safe_optional_string(entry.get("title"))
            source = self._safe_optional_string(entry.get("source"))
            if not url or not title or not source:
                continue

            try:
                items.append(
                    NewsItem.model_validate(
                        {
                            "source": source,
                            "title": title,
                            "url": url,
                            "published_at": self._safe_datetime(entry.get("published_at"), fallback_time),
                            "summary": self._safe_string(entry.get("summary"), self._safe_string(entry.get("content"), "")),
                            "content": self._safe_string(entry.get("content"), self._safe_string(entry.get("summary"), "")),
                        }
                    )
                )
            except ValueError:
                LOGGER.debug("Skipping malformed news item for payload: %s", entry)

        return items

    def _normalize_social_posts(self, payload: Any, fallback_time: datetime) -> list[SocialPost]:
        if not isinstance(payload, list):
            return []

        posts: list[SocialPost] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue

            try:
                post_payload: dict[str, Any] = {
                    "platform": self._safe_string(entry.get("platform"), "Unknown"),
                    "author": self._safe_string(entry.get("author"), "unknown"),
                    "published_at": self._safe_datetime(entry.get("published_at"), fallback_time),
                    "content": self._safe_string(entry.get("content"), ""),
                    "sentiment_hint": self._safe_float(entry.get("sentiment_hint")),
                }
                url = self._safe_optional_string(entry.get("url"))
                if url:
                    post_payload["url"] = url

                posts.append(SocialPost.model_validate(post_payload))
            except ValueError:
                LOGGER.debug("Skipping malformed social post for payload: %s", entry)

        return posts

    @staticmethod
    def _fundamentals_snapshot(fundamentals: FundamentalsData | None) -> dict[str, float | str | None]:
        if fundamentals is None:
            return {
                "pe_ratio": None,
                "pb_ratio": None,
                "roe": None,
                "roce": None,
                "debt_to_equity": None,
                "sales_growth": None,
                "profit_growth": None,
            }

        return {
            "pe_ratio": fundamentals.pe_ratio,
            "pb_ratio": fundamentals.pb_ratio,
            "roe": fundamentals.roe,
            "roce": fundamentals.roce,
            "debt_to_equity": fundamentals.debt_to_equity,
            "sales_growth": fundamentals.sales_growth,
            "profit_growth": fundamentals.profit_growth,
            "source_url": str(fundamentals.source_url) if fundamentals.source_url else None,
        }

    @staticmethod
    def _normalize_string_list(payload: Any) -> list[str]:
        if not isinstance(payload, list):
            return []
        values: list[str] = []
        for item in payload:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                values.append(text)
        return values

    @staticmethod
    def _safe_string(value: Any, default: str) -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text if text else default

    @staticmethod
    def _safe_optional_string(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text if text else None

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        if value in (None, "", "null"):
            return None
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        return parsed if math.isfinite(parsed) else None

    @staticmethod
    def _safe_datetime(value: Any, default: datetime | None = None) -> datetime:
        fallback = default or datetime.now(timezone.utc)
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, str) and value.strip():
            normalized = value.replace("Z", "+00:00")
            try:
                parsed = datetime.fromisoformat(normalized)
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                return fallback
        return fallback

    @staticmethod
    def _truncate(text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return f"{text[: limit - 3].rstrip()}..."


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a saved stock snapshot from data/raw.")
    parser.add_argument("ticker", help="Ticker to analyze, e.g. RELIANCE")
    parser.add_argument(
        "--raw-data-dir",
        type=Path,
        default=RAW_DATA_DIR,
        help="Directory containing raw stock JSON snapshots.",
    )
    args = parser.parse_args()

    analyzer = RawStockAnalyzer(raw_data_dir=args.raw_data_dir)
    result = analyzer.analyze_ticker(args.ticker)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
