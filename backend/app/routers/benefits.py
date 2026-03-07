from fastapi import APIRouter, Query
from app.schemas.benefits import EligibilityInput, EligibilityResult, BenefitProgram, HealthCenter
from app.services.benefits_engine import get_eligibility_result, find_health_centers, _load_programs

router = APIRouter()


@router.post("/check", response_model=EligibilityResult)
async def check_eligibility(input_data: EligibilityInput):
    return await get_eligibility_result(input_data)


@router.get("/programs", response_model=list[BenefitProgram])
async def list_programs(
    state: str = Query("", description="Filter by state code"),
    category: str = Query("", description="Filter by category"),
):
    programs = _load_programs()
    results = []
    for p in programs:
        if state and p.get("states") != ["ALL"] and state.upper() not in p.get("states", []):
            continue
        if category and p.get("category") != category:
            continue
        results.append(BenefitProgram(**p))
    return results


@router.get("/health-centers", response_model=list[HealthCenter])
async def get_health_centers(
    zip: str = Query(..., min_length=3),
    radius: int = Query(30, ge=1, le=100),
):
    return await find_health_centers(zip, radius)
