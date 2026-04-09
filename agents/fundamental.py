from __future__ import annotations

from collectors.models import FullStockData

from agents.base import AgentOutput, BaseAnalysisAgent


class FundamentalAnalysisAgent(BaseAnalysisAgent):
    name = "fundamental"

    def build_prompt(self, stock_data: FullStockData) -> str:
        fundamentals = stock_data.fundamentals
        return (
            f"Analyze the fundamentals of {stock_data.ticker} based on these metrics:\n"
            f"{fundamentals.model_dump_json(indent=2) if fundamentals else 'No fundamentals data available.'}\n"
            "Return JSON with score, findings, and summary."
        )

    def fallback_analysis(self, stock_data: FullStockData) -> AgentOutput:
        fundamentals = stock_data.fundamentals
        if fundamentals is None:
            return AgentOutput(
                agent=self.name,
                score=0.0,
                findings=["Fundamental data is unavailable, so conviction is neutral."],
                summary="No Screener-based fundamentals could be retrieved.",
            )

        score = 0.0
        findings: list[str] = []

        if fundamentals.roe is not None:
            if fundamentals.roe >= 15:
                score += 0.2
                findings.append(f"ROE at {fundamentals.roe:.1f}% suggests efficient capital deployment.")
            else:
                score -= 0.1
                findings.append(f"ROE at {fundamentals.roe:.1f}% is below an ideal quality threshold.")

        if fundamentals.roce is not None:
            if fundamentals.roce >= 15:
                score += 0.2
                findings.append(f"ROCE at {fundamentals.roce:.1f}% indicates solid operating returns.")
            else:
                score -= 0.1
                findings.append(f"ROCE at {fundamentals.roce:.1f}% leaves less margin for execution misses.")

        if fundamentals.debt_to_equity is not None:
            if fundamentals.debt_to_equity <= 0.5:
                score += 0.15
                findings.append("Debt to equity is conservative, reducing balance sheet risk.")
            elif fundamentals.debt_to_equity >= 1.0:
                score -= 0.2
                findings.append("Leverage is elevated and could pressure downside resilience.")

        if fundamentals.pe_ratio is not None:
            if fundamentals.pe_ratio <= 25:
                score += 0.15
                findings.append(f"P/E near {fundamentals.pe_ratio:.1f} is still digestible for Indian large caps.")
            elif fundamentals.pe_ratio >= 40:
                score -= 0.2
                findings.append(f"P/E near {fundamentals.pe_ratio:.1f} implies a rich valuation base.")

        if fundamentals.sales_growth is not None:
            if fundamentals.sales_growth >= 10:
                score += 0.15
                findings.append(f"Sales growth of {fundamentals.sales_growth:.1f}% supports revenue momentum.")
            elif fundamentals.sales_growth < 5:
                score -= 0.1
                findings.append("Sales growth is muted relative to a bullish growth case.")

        if fundamentals.profit_growth is not None:
            if fundamentals.profit_growth >= 10:
                score += 0.15
                findings.append(f"Profit growth of {fundamentals.profit_growth:.1f}% backs earnings expansion.")
            elif fundamentals.profit_growth < 5:
                score -= 0.15
                findings.append("Profit growth is weak, which can cap rerating potential.")

        score = max(-1.0, min(1.0, round(score, 3)))
        summary = (
            "Fundamental view leans positive."
            if score > 0.2
            else "Fundamental view is balanced."
            if score >= -0.2
            else "Fundamental view leans cautious."
        )
        return AgentOutput(agent=self.name, score=score, findings=findings, summary=summary)
