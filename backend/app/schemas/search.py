from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from app.schemas.benefits import BenefitProgram, EligibilityInput
from app.schemas.insurance import InsurancePlan
from app.schemas.medicine import Drug


class ConfidenceLevel(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class OptionType(str, Enum):
    medicine = "medicine"
    provider_service = "provider_service"


class RankedCostOption(BaseModel):
    option_id: str
    option_type: OptionType
    name: str
    provider_name: str
    category: str
    location: str
    distance_miles: float | None = None
    list_price: float
    insured_estimate: float | None = None
    benefit_adjusted_cost: float
    confidence: ConfidenceLevel
    source: str
    network_status: str
    rank_score: float
    explanation: list[str]


class UnifiedSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Medicine or healthcare service term")
    zip_code: str = ""
    quantity: int = Field(default=30, ge=1, le=365)
    include_medicines: bool = True
    include_providers: bool = False
    max_results: int = Field(default=10, ge=1, le=25)
    household: EligibilityInput
    insurance_plan: InsurancePlan | None = None
    deductible_progress: float = Field(
        default=0.0,
        ge=0,
        le=1,
        description="0 means deductible untouched, 1 means fully met",
    )
    oop_progress: float = Field(
        default=0.0,
        ge=0,
        le=1,
        description="0 means no OOP spend, 1 means OOP max already reached",
    )


class UnifiedSearchSummary(BaseModel):
    min_cash_price: float | None = None
    min_insured_price: float | None = None
    min_benefit_adjusted_price: float | None = None
    estimated_annual_benefit_subsidy: float


class MedicineAlternative(BaseModel):
    drug: Drug
    alternative_type: str
    reason: str
    estimated_lowest_price: float | None = None


class MedicineFocus(BaseModel):
    primary_match: Drug | None = None
    medicine_match_count: int
    alternatives: list[MedicineAlternative]


class UnifiedSearchResponse(BaseModel):
    query: str
    zip_code: str
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    fpl_percentage: float
    medicine_focus: MedicineFocus
    eligible_programs: list[BenefitProgram]
    ranked_options: list[RankedCostOption]
    summary: UnifiedSearchSummary
    assumptions: list[str]
