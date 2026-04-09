from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from collectors.models import FullStockData
from utils.llm import LLMConfigurationError, LLMRequestError, complete_json

from agents.base import AgentOutput, InvestmentReport
from agents.fundamental import FundamentalAnalysisAgent
from agents.sentiment import SentimentAnalysisAgent
from agents.technical import TechnicalAnalysisAgent


class AnalysisOrchestrator:
    def __init__(self) -> None:
        self.agents = [
            FundamentalAnalysisAgent(),
            TechnicalAnalysisAgent(),
            SentimentAnalysisAgent(),
        ]

    def run_agents(self, stock_data: FullStockData) -> dict[str, AgentOutput]:
        outputs: dict[str, AgentOutput] = {}
        with ThreadPoolExecutor(max_workers=len(self.agents)) as executor:
            future_map = {executor.submit(agent.analyze, stock_data): agent.name for agent in self.agents}
            for future in as_completed(future_map):
                output = future.result()
                outputs[output.agent] = output
        return outputs

    def analyze(self, stock_data: FullStockData) -> InvestmentReport:
        agent_outputs = self.run_agents(stock_data)
        try:
            payload = complete_json(
                system_prompt=(
                    "You are a portfolio strategist for Indian equities. "
                    "Return only valid JSON with conviction_score, bull_case, bear_case, risks, recommendation. "
                    "Set conviction_score between -1 and 1."
                ),
                user_prompt=(
                    f"Ticker: {stock_data.ticker}\n"
                    f"Current price: {stock_data.current_price}\n"
                    f"Errors: {stock_data.errors}\n"
                    f"Agent outputs: {[output.model_dump(mode='json') for output in agent_outputs.values()]}\n"
                    "Synthesize a balanced investment report."
                ),
                temperature=0.15,
                max_tokens=1200,
            )
            payload["ticker"] = stock_data.ticker
            payload["agent_outputs"] = agent_outputs
            return InvestmentReport.model_validate(payload)
        except (LLMConfigurationError, LLMRequestError, ValueError):
            return self._fallback_report(stock_data, agent_outputs)

    def _fallback_report(
        self,
        stock_data: FullStockData,
        agent_outputs: dict[str, AgentOutput],
    ) -> InvestmentReport:
        conviction_score = round(
            sum(output.score for output in agent_outputs.values()) / max(len(agent_outputs), 1),
            3,
        )

        bull_case = self._pick_findings(agent_outputs, positive=True)
        bear_case = self._pick_findings(agent_outputs, positive=False)
        risks = bear_case[:2]
        if stock_data.errors:
            risks.append(f"Data coverage was partial: {'; '.join(stock_data.errors)}")

        if conviction_score >= 0.45:
            recommendation = "Buy"
        elif conviction_score >= 0.1:
            recommendation = "Accumulate"
        elif conviction_score <= -0.45:
            recommendation = "Avoid"
        elif conviction_score <= -0.1:
            recommendation = "Reduce"
        else:
            recommendation = "Hold"

        if not bull_case:
            bull_case = ["No strong upside factors were confirmed beyond a neutral baseline."]
        if not bear_case:
            bear_case = ["No major downside catalyst was strongly confirmed in the current snapshot."]
        if not risks:
            risks = ["Market-wide volatility can still invalidate a neutral-to-positive setup."]

        return InvestmentReport(
            ticker=stock_data.ticker,
            conviction_score=conviction_score,
            bull_case=bull_case,
            bear_case=bear_case,
            risks=risks,
            recommendation=recommendation,
            agent_outputs=agent_outputs,
        )

    @staticmethod
    def _pick_findings(agent_outputs: dict[str, AgentOutput], positive: bool) -> list[str]:
        ordered = sorted(agent_outputs.values(), key=lambda output: output.score, reverse=positive)
        selected: list[str] = []
        for output in ordered:
            if positive and output.score <= 0:
                continue
            if not positive and output.score >= 0:
                continue
            selected.extend(output.findings[:2])
        return selected[:4]
