from __future__ import annotations

import logging
from typing import Final

import pandas as pd
import yfinance as yf

from collectors.models import PriceData
from utils.retry import retry

LOGGER = logging.getLogger(__name__)
SUPPORTED_SUFFIXES: Final[tuple[str, ...]] = (".NS", ".BO")


def _candidate_symbols(ticker: str) -> list[str]:
    ticker = ticker.upper().strip()
    if ticker.endswith(SUPPORTED_SUFFIXES):
        return [ticker]
    return [f"{ticker}{suffix}" for suffix in SUPPORTED_SUFFIXES]


def _build_price_rows(
    symbol: str,
    history: pd.DataFrame,
    current_price: float | None,
) -> list[PriceData]:
    exchange = "NS" if symbol.endswith(".NS") else "BO" if symbol.endswith(".BO") else "UNKNOWN"
    rows: list[PriceData] = []
    for index, row in history.iterrows():
        rows.append(
            PriceData(
                symbol=symbol,
                exchange=exchange,
                timestamp=index.to_pydatetime(),
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=int(row["Volume"]),
                current_price=current_price,
            )
        )
    return rows


@retry(attempts=3, delay_seconds=1.5)
def _fetch_symbol_history(symbol: str) -> tuple[list[PriceData], float | None]:
    ticker = yf.Ticker(symbol)
    history = ticker.history(period="90d", interval="1d", auto_adjust=False)
    if history.empty:
        raise ValueError(f"No price history returned for {symbol}")

    current_price = None
    fast_info = getattr(ticker, "fast_info", None)
    if fast_info is not None:
        current_price = fast_info.get("lastPrice") or fast_info.get("last_price")
    if current_price is None:
        current_price = float(history["Close"].iloc[-1])

    rows = _build_price_rows(symbol=symbol, history=history, current_price=float(current_price))
    return rows, float(current_price)


def collect_price_data(ticker: str) -> tuple[list[PriceData], str, float | None]:
    errors: list[str] = []
    for candidate in _candidate_symbols(ticker):
        try:
            rows, current_price = _fetch_symbol_history(candidate)
            return rows, candidate, current_price
        except Exception as exc:  # pragma: no cover - network/data variability
            LOGGER.warning("Failed price collection for %s: %s", candidate, exc)
            errors.append(f"{candidate}: {exc}")

    joined_errors = "; ".join(errors) if errors else "unknown error"
    raise ValueError(f"Unable to resolve ticker {ticker}. {joined_errors}")
