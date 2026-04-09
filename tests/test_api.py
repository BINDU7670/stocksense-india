from __future__ import annotations

from fastapi.testclient import TestClient

from agents.analyze import StructuredAnalysis
from api.main import app
from api.dependencies import get_analysis_service


class StubService:
    def analyze_ticker(self, ticker: str) -> StructuredAnalysis:
        return self._build_analysis(ticker)

    @staticmethod
    def _build_analysis(ticker: str) -> StructuredAnalysis:
        return StructuredAnalysis(
            ticker=ticker.upper(),
            sentiment_summary="Overall sentiment is constructive.",
            key_insights=["Momentum is constructive."],
            risks=["Execution risk."],
            final_recommendation="Buy",
        )


def test_api_endpoints(monkeypatch) -> None:
    app.dependency_overrides[get_analysis_service] = lambda: StubService()
    client = TestClient(app)

    analyze_response = client.get("/analyze/RELIANCE")
    report_response = client.get("/report/RELIANCE")

    assert analyze_response.status_code == 200
    assert report_response.status_code == 200
    assert analyze_response.json()["ticker"] == "RELIANCE"
    assert analyze_response.json()["final_recommendation"] == "Buy"

    app.dependency_overrides.clear()
