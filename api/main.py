from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers.analysis import router as analysis_router
from api.routers.health import router as health_router
from api.services.analysis_service import AnalysisService
from utils.settings import ensure_directories


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_directories()
    app.state.analysis_service = AnalysisService()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="StockSense India API",
        version="1.0.0",
        description="Production-ready FastAPI backend for StockSense India stock analysis.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(analysis_router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("PORT") or os.getenv("API_PORT", "10000")),
        reload=False,
    )
