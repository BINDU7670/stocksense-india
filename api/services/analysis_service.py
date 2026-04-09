from __future__ import annotations

import logging
from pathlib import Path

from agents.analyze import RawStockAnalyzer, StructuredAnalysis
from utils.settings import RAW_DATA_DIR, ensure_directories

LOGGER = logging.getLogger(__name__)


class AnalysisServiceError(RuntimeError):
    """Base service error for API-layer analysis failures."""


class SnapshotNotFoundError(AnalysisServiceError):
    """Raised when the requested raw snapshot file does not exist."""


class InvalidTickerError(AnalysisServiceError):
    """Raised when the ticker input is empty or malformed."""


class AnalysisService:
    def __init__(
        self,
        analyzer: RawStockAnalyzer | None = None,
        raw_data_dir: Path | None = None,
    ) -> None:
        ensure_directories()
        self.raw_data_dir = raw_data_dir or RAW_DATA_DIR
        self.analyzer = analyzer or RawStockAnalyzer(raw_data_dir=self.raw_data_dir)

    def analyze_ticker(self, ticker: str) -> StructuredAnalysis:
        normalized_ticker = self._normalize_ticker(ticker)
        try:
            return self.analyzer.analyze_ticker(normalized_ticker)
        except FileNotFoundError as exc:
            raise SnapshotNotFoundError(
                f"Raw snapshot for ticker '{normalized_ticker}' was not found in {self.raw_data_dir}."
            ) from exc
        except ValueError as exc:
            raise InvalidTickerError(str(exc)) from exc
        except AnalysisServiceError:
            raise
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            LOGGER.exception("Unexpected analysis failure for %s", normalized_ticker)
            raise AnalysisServiceError("Unable to complete stock analysis.") from exc

    @staticmethod
    def _normalize_ticker(ticker: str) -> str:
        normalized = ticker.upper().strip()
        if not normalized:
            raise InvalidTickerError("Ticker must not be empty.")
        return normalized
