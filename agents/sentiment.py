from __future__ import annotations

from collectors.models import FullStockData

from agents.base import AgentOutput, BaseAnalysisAgent


class SentimentAnalysisAgent(BaseAnalysisAgent):
    name = "sentiment"

    def build_prompt(self, stock_data: FullStockData) -> str:
        news_titles = [item.title for item in stock_data.news[:5]]
        social_posts = [item.content for item in stock_data.social_posts[:5]]
        return (
            f"Assess market sentiment for {stock_data.ticker} using these news titles: {news_titles}\n"
            f"and social commentary: {social_posts}\n"
            "Return JSON with score, findings, and summary."
        )

    def fallback_analysis(self, stock_data: FullStockData) -> AgentOutput:
        scores = [post.sentiment_hint for post in stock_data.social_posts if post.sentiment_hint is not None]
        news_text = " ".join(f"{item.title} {item.summary} {item.content}" for item in stock_data.news).lower()

        positive_terms = ("growth", "beat", "upside", "strong", "bullish", "expansion")
        negative_terms = ("debt", "probe", "downgrade", "fall", "bearish", "weak")
        positive_hits = sum(term in news_text for term in positive_terms)
        negative_hits = sum(term in news_text for term in negative_terms)

        news_score = 0.0
        if positive_hits or negative_hits:
            news_score = (positive_hits - negative_hits) / (positive_hits + negative_hits)

        social_score = sum(scores) / len(scores) if scores else 0.0
        combined = round((news_score + social_score) / 2, 3)

        findings = [
            f"News-derived sentiment score is {news_score:.2f}.",
            f"Retail and social chatter sentiment score is {social_score:.2f}.",
            f"Combined sentiment lands at {combined:.2f}.",
        ]
        summary = (
            "Narrative sentiment is supportive."
            if combined > 0.2
            else "Narrative sentiment is balanced."
            if combined >= -0.2
            else "Narrative sentiment is cautious."
        )
        return AgentOutput(agent=self.name, score=combined, findings=findings, summary=summary)
