from pydantic import BaseModel
from enum import Enum
from app.schemas.insurance import InsurancePlan


class ServiceType(str, Enum):
    office_visit = "office_visit"
    specialist = "specialist"
    urgent_care = "urgent_care"
    er = "er"
    prescription = "prescription"
    procedure = "procedure"
    preventive = "preventive"
    lab = "lab"
    imaging = "imaging"


class CostScenario(BaseModel):
    service_type: ServiceType
    service_name: str
    retail_price: float
    frequency: int


class CostCalculationRequest(BaseModel):
    insurance_plan: InsurancePlan
    scenarios: list[CostScenario]


class CostLineItem(BaseModel):
    service_name: str
    retail_price: float
    frequency: int
    annual_retail_cost: float
    annual_insured_cost: float
    deductible_applied: float
    copay_applied: float
    coinsurance_applied: float
    insurance_paid: float
    savings: float


class CostCalculationResult(BaseModel):
    line_items: list[CostLineItem]
    totals: dict
    recommendation: str
