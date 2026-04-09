from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from collectors.models import FullStockData
from utils.llm import LLMConfigurationError, LLMRequestError, complete_json


class AgentOutput(BaseModel):
    agent: str
    score: float = Field(ge=-1.0, le=1.0)
    findings: list[str] = Field(default_factory=list)
    summary: str


class InvestmentReport(BaseModel):
    ticker: str
    conviction_score: float = Field(ge=-1.0, le=1.0)
    bull_case: list[str] = Field(default_factory=list)
    bear_case: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommendation: str
    agent_outputs: dict[str, AgentOutput] = Field(default_factory=dict)


class BaseAnalysisAgent(ABC):
    name = "base"

    def analyze(self, stock_data: FullStockData) -> AgentOutput:
        system_prompt = (
            "You are an Indian equity research specialist. "
            "Return only valid JSON with keys score, findings, and summary. "
            "Keep score between -1 and 1 and findings as concise bullet-style sentences."
        )
        try:
            payload = complete_json(
                system_prompt=system_prompt,
                user_prompt=self.build_prompt(stock_data),
                temperature=0.1,
                max_tokens=800,
            )
            payload["agent"] = self.name
            return AgentOutput.model_validate(payload)
        except (LLMConfigurationError, LLMRequestError, ValueError):
            return self.fallback_analysis(stock_data)

    @abstractmethod
    def build_prompt(self, stock_data: FullStockData) -> str:
        """Build a focused LLM prompt for the agent."""

    @abstractmethod
    def fallback_analysis(self, stock_data: FullStockData) -> AgentOutput:
        """Provide a deterministic analysis when LLM access is unavailable."""
