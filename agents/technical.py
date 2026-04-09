from __future__ import annotations

import math

from collectors.models import FullStockData

from agents.base import AgentOutput, BaseAnalysisAgent


class TechnicalAnalysisAgent(BaseAnalysisAgent):
    name = "technical"

    def build_prompt(self, stock_data: FullStockData) -> str:
        closes = [row.close for row in stock_data.price_history[-10:]]
        return (
            f"Analyze the price action of {stock_data.ticker} from the latest closes {closes}. "
            f"Current price is {stock_data.current_price}. "
            "Return JSON with score, findings, and summary."
        )

    def fallback_analysis(self, stock_data: FullStockData) -> AgentOutput:
        prices = stock_data.price_history
        if len(prices) < 20:
            return AgentOutput(
                agent=self.name,
                score=0.0,
                findings=["Insufficient price history for a reliable technical read."],
                summary="Technical signal is neutral because the time series is too short.",
            )

        closes = [row.close for row in prices]
        latest = closes[-1]
        sma20 = sum(closes[-20:]) / 20
        sma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else sma20
        return_90d = ((latest / closes[0]) - 1.0) * 100 if closes[0] else 0.0
        daily_returns = [
            ((closes[index] / closes[index - 1]) - 1.0) * 100
            for index in range(1, len(closes))
            if closes[index - 1]
        ]
        volatility = math.sqrt(sum(value * value for value in daily_returns) / len(daily_returns))

        score = 0.0
        findings: list[str] = []

        if latest > sma20:
            score += 0.2
            findings.append("Price is trading above the 20-day average, signaling short-term strength.")
        else:
            score -= 0.15
            findings.append("Price is below the 20-day average, showing weaker near-term momentum.")

        if latest > sma50:
            score += 0.2
            findings.append("Price is above the 50-day average, which supports trend continuation.")
        else:
            score -= 0.15
            findings.append("Price is below the 50-day average, so the trend backdrop is softer.")

        if return_90d >= 8:
            score += 0.2
            findings.append(f"Roughly {return_90d:.1f}% appreciation over 90 days reflects positive momentum.")
        elif return_90d <= -8:
            score -= 0.25
            findings.append(f"About {return_90d:.1f}% over 90 days points to a clear drawdown regime.")

        if volatility <= 2:
            score += 0.1
            findings.append("Daily volatility remains contained, which improves technical quality.")
        elif volatility >= 3.5:
            score -= 0.15
            findings.append("Elevated volatility increases the chance of sharp mean reversion.")

        score = max(-1.0, min(1.0, round(score, 3)))
        summary = (
            "Technical setup is constructive."
            if score > 0.2
            else "Technical setup is mixed."
            if score >= -0.2
            else "Technical setup is under pressure."
        )
        return AgentOutput(agent=self.name, score=score, findings=findings, summary=summary)
