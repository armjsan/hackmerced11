from pydantic import BaseModel
from typing import Optional


class BenefitProgram(BaseModel):
    id: str
    name: str
    type: str
    category: str
    description: str
    eligibility_summary: str
    income_limit_fpl_percent: Optional[float] = None
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    requires_children: bool
    requires_disability: bool
    requires_pregnancy: bool
    states: list[str]
    application_url: str
    phone: str
    estimated_savings: str


class HealthCenter(BaseModel):
    name: str
    address: str
    phone: str
    distance_miles: float
    services: list[str]
    sliding_scale: bool
    website: str


class EligibilityInput(BaseModel):
    annual_income: float
    household_size: int
    state: str
    age: int
    has_children: bool = False
    is_pregnant: bool = False
    has_disability: bool = False
    currently_insured: bool = False
    zip_code: str = ""


class EligibilityResult(BaseModel):
    eligible_programs: list[BenefitProgram]
    nearby_health_centers: list[HealthCenter]
    fpl_percentage: float
    summary: str
