from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

from collectors.fundamentals import collect_fundamentals_data
from collectors.models import FullStockData, FundamentalsData
from collectors.news import collect_news_data
from collectors.price import collect_price_data
from collectors.social import collect_social_data
from utils.settings import RAW_DATA_DIR, ensure_directories

LOGGER = logging.getLogger(__name__)


CollectorFn = Callable[[str], object]


def _save_snapshot(stock_data: FullStockData) -> Path:
    ensure_directories()
    output_path = RAW_DATA_DIR / f"{stock_data.ticker.upper()}.json"
    output_path.write_text(stock_data.model_dump_json(indent=2), encoding="utf-8")
    return output_path


def collect_full_stock_data(ticker: str) -> FullStockData:
    normalized_ticker = ticker.upper().strip()
    stock_data = FullStockData(ticker=normalized_ticker)

    collector_map: dict[str, CollectorFn] = {
        "price": collect_price_data,
        "fundamentals": collect_fundamentals_data,
        "news": collect_news_data,
        "social": collect_social_data,
    }

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_map = {
            executor.submit(collector, normalized_ticker): name
            for name, collector in collector_map.items()
        }

        for future in as_completed(future_map):
            name = future_map[future]
            try:
                result = future.result()
                if name == "price":
                    price_history, resolved_symbol, current_price = result
                    stock_data.price_history = list(price_history)
                    stock_data.resolved_symbol = resolved_symbol
                    stock_data.current_price = current_price
                elif name == "fundamentals":
                    stock_data.fundamentals = result if isinstance(result, FundamentalsData) else None
                elif name == "news":
                    stock_data.news = list(result) if isinstance(result, list) else []
                elif name == "social":
                    stock_data.social_posts = list(result) if isinstance(result, list) else []
            except Exception as exc:  # pragma: no cover - network variability
                LOGGER.exception("Collector %s failed for %s", name, normalized_ticker)
                stock_data.errors.append(f"{name}: {exc}")

    _save_snapshot(stock_data)
    return stock_data


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Collect market data for an Indian stock ticker.")
    parser.add_argument("ticker", help="Ticker symbol, e.g. RELIANCE or TATAMOTORS")
    args = parser.parse_args()

    payload = collect_full_stock_data(args.ticker)
    print(json.dumps(payload.model_dump(mode="json"), indent=2))
