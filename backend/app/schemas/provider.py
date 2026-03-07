from pydantic import BaseModel
from typing import Optional


class Address(BaseModel):
    street: str
    city: str
    state: str
    zip: str


class Provider(BaseModel):
    npi: str
    name: str
    provider_type: str
    specialty: str
    facility_type: str
    address: Address
    phone: str
    accepts_medicaid: bool
    accepts_medicare: bool
    sliding_scale: bool
    distance_miles: Optional[float] = None


class ProcedurePrice(BaseModel):
    cpt_code: str
    procedure_name: str
    cash_price: float
    medicare_rate: Optional[float] = None
    estimated_insured_price: Optional[float] = None
    price_range_low: float
    price_range_high: float


class ProviderDetail(Provider):
    procedure_prices: list[ProcedurePrice]
    hours: str
    website: Optional[str] = None
    rating: Optional[float] = None
