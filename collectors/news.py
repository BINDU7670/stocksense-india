from __future__ import annotations

import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Final
from urllib.parse import quote

import feedparser
import requests

from collectors.models import NewsItem
from utils.retry import retry

LOGGER = logging.getLogger(__name__)
RSS_FEEDS: Final[dict[str, str]] = {
    "Moneycontrol": "https://www.moneycontrol.com/rss/business.xml",
    "ET Markets": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
}


def _parse_datetime(raw_value: str | None) -> datetime:
    if not raw_value:
        return datetime.now(timezone.utc)
    parsed = parsedate_to_datetime(raw_value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


@retry(attempts=3, delay_seconds=1.0)
def _fetch_article_text(url: str) -> str:
    normalized_url = url.removeprefix("https://").removeprefix("http://")
    reader_url = f"https://r.jina.ai/http://{quote(normalized_url, safe='/:?=&')}"
    response = requests.get(reader_url, timeout=25)
    response.raise_for_status()
    text = response.text.strip()
    return text[:5000]


def _matches_ticker(ticker: str, title: str, summary: str) -> bool:
    normalized = ticker.upper().replace(".NS", "").replace(".BO", "")
    haystack = f"{title} {summary}".upper()
    return normalized in haystack


def collect_news_data(ticker: str, limit_per_feed: int = 3) -> list[NewsItem]:
    collected: list[NewsItem] = []
    normalized = ticker.upper()

    for source, feed_url in RSS_FEEDS.items():
        try:
            parsed = feedparser.parse(feed_url)
            count = 0
            for entry in parsed.entries:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", "").strip()
                url = entry.get("link")
                if not url or not title:
                    continue
                if not _matches_ticker(normalized, title, summary):
                    continue

                content = ""
                try:
                    content = _fetch_article_text(url)
                except Exception as exc:  # pragma: no cover - network variability
                    LOGGER.warning("Failed Jina Reader fetch for %s: %s", url, exc)
                    content = summary

                collected.append(
                    NewsItem(
                        source=source,
                        title=title,
                        url=url,
                        published_at=_parse_datetime(entry.get("published")),
                        summary=summary[:500],
                        content=content,
                    )
                )
                count += 1
                if count >= limit_per_feed:
                    break
        except Exception as exc:  # pragma: no cover - network variability
            LOGGER.warning("Failed RSS fetch for %s: %s", source, exc)

    return sorted(collected, key=lambda item: item.published_at, reverse=True)
