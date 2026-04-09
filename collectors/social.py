from __future__ import annotations

from datetime import datetime, timedelta, timezone

from collectors.models import SocialPost


def collect_social_data(ticker: str) -> list[SocialPost]:
    normalized = ticker.upper().replace(".NS", "").replace(".BO", "")
    now = datetime.now(timezone.utc)

    return [
        SocialPost(
            platform="Reddit",
            author="u/valuehunter_india",
            published_at=now - timedelta(hours=4),
            content=(
                f"{normalized} keeps showing up in retail discussions because the valuation "
                "looks reasonable if earnings hold up through the next two quarters."
            ),
            url=f"https://www.reddit.com/search/?q={normalized}",
            sentiment_hint=0.35,
        ),
        SocialPost(
            platform="X",
            author="@dalalstreetpulse",
            published_at=now - timedelta(hours=2),
            content=(
                f"Mixed sentiment around {normalized}: traders like the momentum setup, "
                "but many are still cautious on macro headwinds and execution risk."
            ),
            url=f"https://x.com/search?q={normalized}",
            sentiment_hint=0.05,
        ),
        SocialPost(
            platform="StockTwits",
            author="india_momentum_lab",
            published_at=now - timedelta(minutes=45),
            content=(
                f"{normalized} discussion volume is elevated after recent price action. "
                "Bullish posts cite breakout potential; bearish posts point to near-term volatility."
            ),
            url=f"https://stocktwits.com/symbol/{normalized}",
            sentiment_hint=0.1,
        ),
    ]
