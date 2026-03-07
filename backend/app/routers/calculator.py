from fastapi import APIRouter
from app.schemas.calculator import CostCalculationRequest, CostCalculationResult, CostScenario
from app.services.cost_calculator import compute_costs, get_default_scenarios

router = APIRouter()


@router.post("/compute", response_model=CostCalculationResult)
async def calculate_costs(request: CostCalculationRequest):
    return compute_costs(request)


@router.get("/scenarios", response_model=list[CostScenario])
async def get_scenarios():
    return get_default_scenarios()
