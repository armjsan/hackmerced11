from fastapi import APIRouter, Query
from app.services.drug_search import search_drugs, autocomplete_drugs
from app.services.drug_pricing import get_drug_price_comparison
from app.schemas.medicine import DrugSearchResponse, DrugPriceComparison

router = APIRouter()


@router.get("/search", response_model=DrugSearchResponse)
async def search_medicines(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
):
    return await search_drugs(q, limit)


@router.get("/autocomplete")
async def autocomplete_medicines(
    q: str = Query(..., min_length=1),
    limit: int = Query(8, ge=1, le=20),
):
    return await autocomplete_drugs(q, limit)


@router.get("/{ndc}/prices", response_model=DrugPriceComparison)
async def get_medicine_prices(
    ndc: str,
    zip_code: str = Query("", description="ZIP code for location-based pricing"),
    quantity: int = Query(30, ge=1, le=365),
):
    result = get_drug_price_comparison(ndc, quantity, zip_code)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Drug not found")
    return result
