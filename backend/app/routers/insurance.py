from fastapi import APIRouter
from app.schemas.insurance import (
    InsurancePlan,
    InsuranceUploadRequest,
    InsuranceUploadResult,
    PlanType,
)
from app.services.insurance_parser import parse_insurance_document

router = APIRouter()

PLAN_TEMPLATES = [
    InsurancePlan(
        plan_name="Bronze Plan (ACA)",
        plan_type=PlanType.ppo,
        monthly_premium=300,
        annual_deductible_individual=7000,
        annual_deductible_family=14000,
        copay_primary=50,
        copay_specialist=80,
        copay_urgent_care=75,
        copay_er=500,
        copay_generic_rx=20,
        copay_brand_rx=50,
        coinsurance_percent=40,
        out_of_pocket_max_individual=9100,
        out_of_pocket_max_family=18200,
        covers_preventive_free=True,
    ),
    InsurancePlan(
        plan_name="Silver Plan (ACA)",
        plan_type=PlanType.ppo,
        monthly_premium=450,
        annual_deductible_individual=4000,
        annual_deductible_family=8000,
        copay_primary=35,
        copay_specialist=65,
        copay_urgent_care=60,
        copay_er=350,
        copay_generic_rx=15,
        copay_brand_rx=40,
        coinsurance_percent=30,
        out_of_pocket_max_individual=9100,
        out_of_pocket_max_family=18200,
        covers_preventive_free=True,
    ),
    InsurancePlan(
        plan_name="Gold Plan (ACA)",
        plan_type=PlanType.ppo,
        monthly_premium=600,
        annual_deductible_individual=1500,
        annual_deductible_family=3000,
        copay_primary=25,
        copay_specialist=50,
        copay_urgent_care=50,
        copay_er=250,
        copay_generic_rx=10,
        copay_brand_rx=35,
        coinsurance_percent=20,
        out_of_pocket_max_individual=8700,
        out_of_pocket_max_family=17400,
        covers_preventive_free=True,
    ),
    InsurancePlan(
        plan_name="Platinum Plan (ACA)",
        plan_type=PlanType.hmo,
        monthly_premium=750,
        annual_deductible_individual=500,
        annual_deductible_family=1000,
        copay_primary=15,
        copay_specialist=35,
        copay_urgent_care=30,
        copay_er=150,
        copay_generic_rx=5,
        copay_brand_rx=25,
        coinsurance_percent=10,
        out_of_pocket_max_individual=4500,
        out_of_pocket_max_family=9000,
        covers_preventive_free=True,
    ),
    InsurancePlan(
        plan_name="High Deductible (HDHP + HSA)",
        plan_type=PlanType.hdhp,
        monthly_premium=200,
        annual_deductible_individual=3200,
        annual_deductible_family=6400,
        copay_primary=0,
        copay_specialist=0,
        copay_urgent_care=0,
        copay_er=0,
        copay_generic_rx=0,
        copay_brand_rx=0,
        coinsurance_percent=20,
        out_of_pocket_max_individual=8050,
        out_of_pocket_max_family=16100,
        covers_preventive_free=True,
    ),
]


@router.post("/plan", response_model=InsurancePlan)
async def validate_plan(plan: InsurancePlan):
    return plan


@router.post("/upload/parse", response_model=InsuranceUploadResult)
async def parse_uploaded_plan(payload: InsuranceUploadRequest):
    return parse_insurance_document(payload)


@router.get("/templates", response_model=list[InsurancePlan])
async def get_templates():
    return PLAN_TEMPLATES
