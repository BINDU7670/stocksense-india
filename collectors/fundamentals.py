from __future__ import annotations

import logging
import re
from typing import Final

import requests
from bs4 import BeautifulSoup

from collectors.models import FundamentalsData
from utils.retry import retry

LOGGER = logging.getLogger(__name__)
HEADERS: Final[dict[str, str]] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )
}


def _to_float(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = (
        value.replace(",", "")
        .replace("%", "")
        .replace("x", "")
        .replace("₹", "")
        .replace("Rs.", "")
        .strip()
    )
    if not cleaned or cleaned == "-":
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    return float(match.group()) if match else None


def _extract_ratio_map(soup: BeautifulSoup) -> dict[str, float]:
    ratio_map: dict[str, float] = {}
    for item in soup.select("li.flex.flex-space-between"):
        spans = item.find_all("span")
        if len(spans) < 2:
            continue
        label = spans[0].get_text(" ", strip=True).lower()
        value = _to_float(spans[-1].get_text(" ", strip=True))
        if value is not None:
            ratio_map[label] = value
    return ratio_map


def _extract_growth_metrics(soup: BeautifulSoup) -> tuple[float | None, float | None]:
    sales_growth: float | None = None
    profit_growth: float | None = None

    for section in soup.select("section"):
        heading = section.find(["h2", "h3"])
        if heading is None:
            continue
        title = heading.get_text(" ", strip=True).lower()
        if "growth" not in title and "compounded" not in title:
            continue

        for row in section.select("tr"):
            cells = [cell.get_text(" ", strip=True).lower() for cell in row.find_all(["th", "td"])]
            if len(cells) < 2:
                continue
            row_label = cells[0]
            row_value = _to_float(cells[-1])
            if row_value is None:
                continue
            if "sales" in row_label and sales_growth is None:
                sales_growth = row_value
            if "profit" in row_label and profit_growth is None:
                profit_growth = row_value

    return sales_growth, profit_growth


@retry(attempts=3, delay_seconds=1.5)
def collect_fundamentals_data(ticker: str) -> FundamentalsData:
    normalized_ticker = ticker.upper().replace(".NS", "").replace(".BO", "")
    url = f"https://www.screener.in/company/{normalized_ticker}/consolidated/"
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    if soup.find(string=re.compile("Page not found", re.IGNORECASE)):
        raise ValueError(f"Screener page not found for {normalized_ticker}")

    ratios = _extract_ratio_map(soup)
    sales_growth, profit_growth = _extract_growth_metrics(soup)

    return FundamentalsData(
        ticker=normalized_ticker,
        pe_ratio=ratios.get("stock p/e") or ratios.get("p/e"),
        pb_ratio=ratios.get("book value") or ratios.get("price to book value"),
        roe=ratios.get("roe"),
        roce=ratios.get("roce"),
        debt_to_equity=ratios.get("debt to equity"),
        sales_growth=sales_growth,
        profit_growth=profit_growth,
        source_url=url,
    )
