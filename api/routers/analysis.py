from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_analysis_service
from api.models.analysis import AnalysisResponse, ErrorResponse
from api.services.analysis_service import (
    AnalysisService,
    AnalysisServiceError,
    InvalidTickerError,
    SnapshotNotFoundError,
)

router = APIRouter(tags=["analysis"])

ERROR_RESPONSES = {
    status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Raw stock snapshot not found."},
    status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": ErrorResponse, "description": "Ticker input was invalid."},
    status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse, "description": "Analysis execution failed."},
}


@router.get(
    "/analyze/{ticker}",
    response_model=AnalysisResponse,
    responses=ERROR_RESPONSES,
    summary="Analyze a stock from its saved raw snapshot",
)
async def analyze_ticker(
    ticker: str,
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisResponse:
    return await _run_analysis(service=service, ticker=ticker)


@router.post(
    "/analyze/{ticker}",
    response_model=AnalysisResponse,
    responses=ERROR_RESPONSES,
    include_in_schema=False,
)
async def analyze_ticker_post(
    ticker: str,
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisResponse:
    return await _run_analysis(service=service, ticker=ticker)


@router.get(
    "/report/{ticker}",
    response_model=AnalysisResponse,
    responses=ERROR_RESPONSES,
    include_in_schema=False,
)
async def report_alias(
    ticker: str,
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisResponse:
    return await _run_analysis(service=service, ticker=ticker)


async def _run_analysis(service: AnalysisService, ticker: str) -> AnalysisResponse:
    try:
        analysis = await asyncio.to_thread(service.analyze_ticker, ticker)
        return AnalysisResponse.from_domain(analysis)
    except SnapshotNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidTickerError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except AnalysisServiceError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
