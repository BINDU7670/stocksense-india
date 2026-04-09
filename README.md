# StockSense India

StockSense India is a production-oriented SaaS foundation for AI-powered Indian stock analysis. The platform collects multi-source market data, persists a lightweight knowledge graph, runs specialized AI agents, and exposes the final research report through a FastAPI backend and React frontend.

## Architecture

### Phase 1: Data Collection
- `collectors/models.py` defines the typed Pydantic contracts used across the system.
- `collectors/price.py` fetches 90-day OHLCV data from Yahoo Finance for `.NS` and `.BO`.
- `collectors/fundamentals.py` scrapes Screener.in for valuation and quality metrics.
- `collectors/news.py` pulls RSS items from Moneycontrol and ET Markets, then attempts article enrichment through Jina Reader.
- `collectors/social.py` provides low-friction retail sentiment signals without complex authentication.
- `collectors/run.py` executes collectors in parallel, continues on partial failure, and persists snapshots into `data/raw/`.

### Phase 2: Knowledge Graph
- `graph/db.py` persists a Kuzu-style graph simulation backed by JSON for easy local development.
- `graph/schema.py` documents the graph entities and relationships.
- `graph/queries.py` exposes typed query helpers for price history, news retrieval, and sentiment lookups.

### Phase 3: AI Agents
- `utils/llm.py` is the only path for OpenRouter chat completions and uses `qwen/qwen3.6-plus:free`.
- `agents/fundamental.py`, `agents/technical.py`, and `agents/sentiment.py` each return a score, findings, and summary.
- `agents/orchestrator.py` runs the agents in parallel and synthesizes a structured investment report.

### Phase 4: API + Frontend
- `api/main.py` exposes `POST /analyze/{ticker}` and `GET /report/{ticker}`.
- `frontend/` contains a React + Vite client that submits tickers, shows conviction output, and visualizes agent scores.

## Environment

Copy `.env.example` to `.env` and add your OpenRouter key:

```bash
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=qwen/qwen3.6-plus:free
```

## Local Run

### Backend
```bash
pip install -r requirements.txt
uvicorn api.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Docker

```bash
docker compose up --build
```

Backend runs on `http://localhost:8000` and frontend runs on `http://localhost:3000`.

## Render Deployment

Render-native deployment files are included:
- `render.yaml`
- `.python-version`

Recommended Render settings:
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn api.main:app --host 0.0.0.0 --port 10000`
- Health check path: `/health`

The application entrypoint also supports Render's `PORT` environment variable at runtime, with `10000` as the production default.

## API Output

The final report shape is:

```json
{
  "ticker": "RELIANCE",
  "conviction_score": 0.42,
  "bull_case": ["..."],
  "bear_case": ["..."],
  "risks": ["..."],
  "recommendation": "Accumulate",
  "agent_outputs": {
    "fundamental": {
      "agent": "fundamental",
      "score": 0.5,
      "findings": ["..."],
      "summary": "..."
    }
  }
}
```

## Testing

```bash
pytest
```
