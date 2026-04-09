from __future__ import annotations

COMPANY_ENTITY = {
    "label": "Company",
    "primary_key": "ticker",
    "properties": ["ticker", "symbol", "exchange", "current_price", "collected_at"],
}

PRICE_EVENT_ENTITY = {
    "label": "PriceEvent",
    "primary_key": "event_id",
    "properties": ["event_id", "ticker", "timestamp", "open", "high", "low", "close", "volume"],
}

NEWS_ENTITY = {
    "label": "NewsItem",
    "primary_key": "news_id",
    "properties": ["news_id", "ticker", "source", "title", "published_at", "url", "summary"],
}

SOCIAL_ENTITY = {
    "label": "SocialPost",
    "primary_key": "post_id",
    "properties": ["post_id", "ticker", "platform", "author", "published_at", "sentiment_hint"],
}

GRAPH_SCHEMA = {
    "entities": [COMPANY_ENTITY, PRICE_EVENT_ENTITY, NEWS_ENTITY, SOCIAL_ENTITY],
    "relationships": [
        ("Company", "HAS_PRICE_EVENT", "PriceEvent"),
        ("Company", "HAS_NEWS", "NewsItem"),
        ("Company", "HAS_SOCIAL_POST", "SocialPost"),
    ],
}
