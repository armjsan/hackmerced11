from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class PlanType(str, Enum):
    hmo = "hmo"
    ppo = "ppo"
    epo = "epo"
    hdhp = "hdhp"
    pos = "pos"
    other = "other"


class InsurancePlan(BaseModel):
    plan_name: str
    plan_type: PlanType
    monthly_premium: float
    annual_deductible_individual: float
    annual_deductible_family: Optional[float] = None
    copay_primary: float
    copay_specialist: float
    copay_urgent_care: float
    copay_er: float
    copay_generic_rx: float
    copay_brand_rx: float
    coinsurance_percent: float
    out_of_pocket_max_individual: float
    out_of_pocket_max_family: Optional[float] = None
    covers_preventive_free: bool = True
    rx_deductible_separate: bool = False
    rx_deductible_amount: Optional[float] = None


class InsuranceUploadRequest(BaseModel):
    document_text: str = Field(
        ...,
        min_length=10,
        description="Raw text extracted from plan card, SBC, EOB, or policy summary.",
    )
    plan_name_hint: Optional[str] = None


class InsuranceUploadResult(BaseModel):
    parsed_plan: InsurancePlan
    confidence: float
    covered_services: list[str]
    excluded_services: list[str]
    summary: str
    extracted_fields: dict[str, str | float | bool]
