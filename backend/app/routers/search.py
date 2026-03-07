from fastapi import APIRouter
from app.schemas.search import UnifiedSearchRequest, UnifiedSearchResponse
from app.services.search_engine import run_unified_search

router = APIRouter()


@router.post("/true-cost", response_model=UnifiedSearchResponse)
async def true_cost_search(request: UnifiedSearchRequest):
    return await run_unified_search(request)
