import { FormEvent, startTransition, useDeferredValue, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { analyzeTicker } from "./api";
import type { InvestmentReport } from "./types";

const starterTickers = ["RELIANCE", "TATAMOTORS", "INFY", "HDFCBANK"];

function App() {
  const [ticker, setTicker] = useState("RELIANCE");
  const [report, setReport] = useState<InvestmentReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const deferredTicker = useDeferredValue(ticker);

  const chartData = report
    ? Object.values(report.agent_outputs).map((item) => ({
        name: item.agent,
        score: Number(item.score.toFixed(2)),
      }))
    : [];

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const nextReport = await analyzeTicker(ticker.trim());
      startTransition(() => setReport(nextReport));
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-shell">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />

      <main className="app-grid">
        <section className="hero-card">
          <p className="eyebrow">AI Equity Research for India</p>
          <h1>StockSense India</h1>
          <p className="hero-copy">
            Multi-agent stock analysis that combines price action, fundamentals, and market
            narrative into one conviction-led report.
          </p>

          <form className="ticker-form" onSubmit={handleSubmit}>
            <label htmlFor="ticker-input">NSE / BSE Ticker</label>
            <div className="ticker-row">
              <input
                id="ticker-input"
                value={ticker}
                onChange={(event) => setTicker(event.target.value.toUpperCase())}
                placeholder="Enter RELIANCE"
              />
              <button type="submit" disabled={loading || !ticker.trim()}>
                {loading ? "Analyzing..." : "Run Analysis"}
              </button>
            </div>
          </form>

          <div className="starter-strip">
            {starterTickers.map((item) => (
              <button
                key={item}
                type="button"
                className="chip"
                onClick={() => setTicker(item)}
              >
                {item}
              </button>
            ))}
          </div>

          <p className="live-hint">Ready to evaluate: {deferredTicker || "Ticker pending"}</p>
        </section>

        <section className="panel-card">
          {!report && !loading && (
            <div className="empty-state">
              <h2>Structured output, startup-style</h2>
              <p>
                Run an analysis to generate a conviction score, bull and bear cases, risks, and
                per-agent diagnostics.
              </p>
            </div>
          )}

          {error && (
            <div className="status-card error-card">
              <h2>Analysis failed</h2>
              <p>{error}</p>
            </div>
          )}

          {report && (
            <div className="results-stack">
              <div className="headline-row">
                <div>
                  <p className="eyebrow">Latest Report</p>
                  <h2>{report.ticker}</h2>
                </div>
                <div className="score-orb">
                  <span>{report.conviction_score.toFixed(2)}</span>
                  <small>Conviction</small>
                </div>
              </div>

              <div className="summary-band">
                <div>
                  <span>Recommendation</span>
                  <strong>{report.recommendation}</strong>
                </div>
                <div>
                  <span>Agent Count</span>
                  <strong>{Object.keys(report.agent_outputs).length}</strong>
                </div>
              </div>

              <div className="chart-card">
                <h3>Agent Scores</h3>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="4 4" stroke="rgba(255,255,255,0.1)" />
                    <XAxis dataKey="name" stroke="#f5e8cf" />
                    <YAxis domain={[-1, 1]} stroke="#f5e8cf" />
                    <Tooltip />
                    <Bar dataKey="score" fill="#ff8a3d" radius={[12, 12, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="insight-grid">
                <InsightCard title="Bull Case" items={report.bull_case} accent="bull" />
                <InsightCard title="Bear Case" items={report.bear_case} accent="bear" />
                <InsightCard title="Risks" items={report.risks} accent="risk" />
              </div>

              <div className="agent-grid">
                {Object.values(report.agent_outputs).map((agent) => (
                  <article className="agent-card" key={agent.agent}>
                    <div className="agent-header">
                      <h3>{agent.agent}</h3>
                      <span>{agent.score.toFixed(2)}</span>
                    </div>
                    <p>{agent.summary}</p>
                    <ul>
                      {agent.findings.map((finding) => (
                        <li key={finding}>{finding}</li>
                      ))}
                    </ul>
                  </article>
                ))}
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

type InsightCardProps = {
  title: string;
  items: string[];
  accent: "bull" | "bear" | "risk";
};

function InsightCard({ title, items, accent }: InsightCardProps) {
  return (
    <article className={`insight-card ${accent}`}>
      <h3>{title}</h3>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </article>
  );
}

export default App;
