import json
from datetime import date
from pathlib import Path
from app.schemas.medicine import Drug, PharmacyPrice, DrugPriceComparison

DATA_DIR = Path(__file__).parent.parent / "data"
_pharmacy_config: dict = {}
_local_drugs: dict[str, dict] = {}
DEFAULT_PHARMACY_CONFIG: dict[str, dict] = {
    "retail_generic": {
        "display_name": "Neighborhood Pharmacy",
        "pharmacy_type": "retail",
        "markup_multiplier": 3.0,
        "dispensing_fee": 2.5,
        "shipping_fee": 0,
        "coupon_available": False,
    },
    "online_low_cost": {
        "display_name": "LowCost Online Pharmacy",
        "pharmacy_type": "online",
        "markup_multiplier": 2.2,
        "dispensing_fee": 3.0,
        "shipping_fee": 5,
        "coupon_available": False,
    },
}


def _load_pharmacy_config() -> dict:
    global _pharmacy_config
    if not _pharmacy_config:
        try:
            with open(DATA_DIR / "mock_pharmacy_prices.json", encoding="utf-8") as f:
                data = json.load(f)
                _pharmacy_config = data if isinstance(data, dict) else DEFAULT_PHARMACY_CONFIG
        except (FileNotFoundError, json.JSONDecodeError):
            _pharmacy_config = DEFAULT_PHARMACY_CONFIG
    return _pharmacy_config


def _load_local_drugs() -> dict[str, dict]:
    global _local_drugs
    if not _local_drugs:
        try:
            with open(DATA_DIR / "common_drugs.json", encoding="utf-8") as f:
                drugs = json.load(f)
                if isinstance(drugs, list):
                    _local_drugs = {str(d.get("ndc", "")): d for d in drugs if d.get("ndc")}
                else:
                    _local_drugs = {}
        except (FileNotFoundError, json.JSONDecodeError):
            _local_drugs = {}
    return _local_drugs


def get_nadac_price(ndc: str) -> float | None:
    """Look up NADAC acquisition cost per unit for a drug."""
    drugs = _load_local_drugs()
    drug = drugs.get(ndc)
    if drug and drug.get("nadac_per_unit"):
        return drug["nadac_per_unit"]
    return None


def calculate_pharmacy_prices(
    nadac_per_unit: float, quantity: int
) -> list[PharmacyPrice]:
    """Generate pharmacy prices based on NADAC cost and markup models."""
    config = _load_pharmacy_config()
    base_cost = nadac_per_unit * quantity
    today = date.today().isoformat()
    prices = []

    for key, pharmacy in config.items():
        markup = pharmacy.get("markup_multiplier", 3.0)
        dispensing = pharmacy.get("dispensing_fee", 2.0)
        shipping = pharmacy.get("shipping_fee", 0)
        price = base_cost * markup + dispensing + shipping

        # Walmart $4 generics floor
        if key == "walmart" and price < 4.0 and nadac_per_unit < 0.50:
            price = 4.00

        prices.append(PharmacyPrice(
            pharmacy_name=pharmacy.get("display_name", "Unknown Pharmacy"),
            pharmacy_type=pharmacy.get("pharmacy_type", "retail"),
            price=round(price, 2),
            quantity=quantity,
            unit="tablets",
            price_per_unit=round(price / quantity, 4),
            with_coupon=pharmacy.get("coupon_available", False),
            coupon_name=pharmacy.get("coupon_name"),
            last_updated=today,
        ))

    prices.sort(key=lambda p: p.price)
    return prices


def get_drug_price_comparison(
    ndc: str, quantity: int = 30, zip_code: str | None = None
) -> DrugPriceComparison | None:
    """Get full price comparison for a drug by NDC."""
    drugs = _load_local_drugs()
    drug_data = drugs.get(ndc)
    if not drug_data:
        return None

    drug = Drug(
        ndc=str(drug_data.get("ndc", "")),
        brand_name=str(drug_data.get("brand_name", "")),
        generic_name=str(drug_data.get("generic_name", "")),
        dosage_form=str(drug_data.get("dosage_form", "TABLET")),
        strength=str(drug_data.get("strength", "")),
        manufacturer=str(drug_data.get("manufacturer", "Unknown")),
        is_generic=bool(drug_data.get("is_generic", False)),
        rx_required=bool(drug_data.get("rx_required", True)),
    )

    nadac = drug_data.get("nadac_per_unit", 0.10)
    pharmacy_prices = calculate_pharmacy_prices(nadac, quantity)

    prices_list = [p.price for p in pharmacy_prices]
    if not prices_list:
        return None

    # Find generic alternative if this is a brand drug
    generic_alt = None
    if not drug_data.get("is_generic", False):
        for d in drugs.values():
            if (
                d.get("is_generic")
                and str(d.get("generic_name", "")).lower() == str(drug_data.get("generic_name", "")).lower()
                and str(d.get("ndc", "")) != ndc
            ):
                generic_alt = Drug(**{k: d[k] for k in [
                    "ndc", "brand_name", "generic_name", "dosage_form",
                    "strength", "manufacturer", "is_generic", "rx_required"
                ]})
                break

    return DrugPriceComparison(
        drug=drug,
        nadac_price_per_unit=nadac,
        pharmacy_prices=pharmacy_prices,
        lowest_price=min(prices_list),
        highest_price=max(prices_list),
        potential_savings=round(max(prices_list) - min(prices_list), 2),
        generic_alternative=generic_alt,
    )
