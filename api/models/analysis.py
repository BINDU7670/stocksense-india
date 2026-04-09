from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from agents.analyze import StructuredAnalysis


class AnalysisResponse(BaseModel):
    ticker: str
    sentiment_summary: str
    key_insights: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    final_recommendation: Literal["Buy", "Hold", "Sell"]

    @classmethod
    def from_domain(cls, analysis: StructuredAnalysis) -> "AnalysisResponse":
        return cls.model_validate(analysis.model_dump(mode="json"))


class ErrorResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    status: str
