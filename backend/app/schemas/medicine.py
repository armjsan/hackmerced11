from pydantic import BaseModel
from typing import Optional
from enum import Enum


class PharmacyType(str, Enum):
    retail = "retail"
    online = "online"
    mail_order = "mail_order"


class Drug(BaseModel):
    ndc: str
    brand_name: str
    generic_name: str
    dosage_form: str
    strength: str
    manufacturer: str
    is_generic: bool
    rx_required: bool


class PharmacyPrice(BaseModel):
    pharmacy_name: str
    pharmacy_type: PharmacyType
    price: float
    quantity: int
    unit: str
    price_per_unit: float
    with_coupon: bool
    coupon_name: Optional[str] = None
    last_updated: str


class DrugPriceComparison(BaseModel):
    drug: Drug
    nadac_price_per_unit: Optional[float] = None
    pharmacy_prices: list[PharmacyPrice]
    lowest_price: float
    highest_price: float
    potential_savings: float
    generic_alternative: Optional[Drug] = None


class DrugSearchResponse(BaseModel):
    drugs: list[Drug]
    total_count: int
    query: str
