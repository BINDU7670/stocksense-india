from __future__ import annotations

from fastapi import APIRouter

from api.models.analysis import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="API health check")
async def healthcheck() -> HealthResponse:
    return HealthResponse(status="ok")
