from fastapi import APIRouter, Query, HTTPException
from app.services.provider_search import (
    search_providers,
    get_provider_detail,
    get_provider_by_npi,
)
from app.schemas.provider import Provider, ProviderDetail

router = APIRouter()


@router.get("/search", response_model=list[Provider])
async def search_providers_endpoint(
    q: str = Query(..., min_length=1),
    zip: str = Query("", description="ZIP code"),
    radius: int = Query(25, ge=1, le=100),
    type: str = Query("", description="individual or organization"),
    limit: int = Query(20, ge=1, le=50),
):
    return await search_providers(q, zip, radius, type, limit)


@router.get("/{npi}", response_model=ProviderDetail)
async def get_provider(npi: str):
    provider = await get_provider_by_npi(npi)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return get_provider_detail(npi, provider)
