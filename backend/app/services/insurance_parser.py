import re

from app.schemas.insurance import (
    InsurancePlan,
    InsuranceUploadRequest,
    InsuranceUploadResult,
    PlanType,
)

_DEFAULT_VALUES = {
    "monthly_premium": 420.0,
    "annual_deductible_individual": 4000.0,
    "annual_deductible_family": 8000.0,
    "copay_primary": 35.0,
    "copay_specialist": 65.0,
    "copay_urgent_care": 60.0,
    "copay_er": 350.0,
    "copay_generic_rx": 15.0,
    "copay_brand_rx": 40.0,
    "coinsurance_percent": 30.0,
    "out_of_pocket_max_individual": 9100.0,
    "out_of_pocket_max_family": 18200.0,
}


def _extract_money(text: str, keywords: list[str]) -> float | None:
    for keyword in keywords:
        pattern = rf"{keyword}[^\d$]*\$?([0-9]{{1,3}}(?:,[0-9]{{3}})*(?:\.\d+)?)"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            raw = match.group(1).replace(",", "")
            try:
                return float(raw)
            except ValueError:
                continue
    return None


def _extract_percent(text: str, keywords: list[str]) -> float | None:
    for keyword in keywords:
        pattern = rf"{keyword}[^\d]*([0-9]{{1,3}}(?:\.\d+)?)\s*%"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    return None


def _extract_bool_preventive(text: str) -> bool:
    phrase_patterns = [
        r"preventive\s+care[^\n]*100%",
        r"preventive\s+care[^\n]*no\s+charge",
        r"preventive\s+care[^\n]*\$0",
    ]
    for pattern in phrase_patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True
    if re.search(r"preventive\s+care[^\n]*(not\s+covered|excluded)", text, flags=re.IGNORECASE):
        return False
    return True


def _parse_plan_type(text: str) -> PlanType:
    normalized = text.lower()
    if "hdhp" in normalized or "high deductible" in normalized:
        return PlanType.hdhp
    if "hmo" in normalized:
        return PlanType.hmo
    if "epo" in normalized:
        return PlanType.epo
    if "pos" in normalized:
        return PlanType.pos
    if "ppo" in normalized:
        return PlanType.ppo
    return PlanType.other


def _parse_service_list(text: str, marker: str) -> list[str]:
    pattern = rf"{marker}\s*:\s*([^\n]+)"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return []
    values = [entry.strip() for entry in match.group(1).split(",")]
    return [entry for entry in values if entry]


def parse_insurance_document(request: InsuranceUploadRequest) -> InsuranceUploadResult:
    text = request.document_text
    values = dict(_DEFAULT_VALUES)

    extracted: dict[str, str | float | bool] = {}

    mapping_money = {
        "monthly_premium": ["monthly premium", "premium per month", "premium"],
        "annual_deductible_individual": [
            "individual deductible",
            "deductible individual",
            "in network deductible",
            "medical deductible",
        ],
        "annual_deductible_family": ["family deductible", "deductible family"],
        "copay_primary": ["primary care copay", "pcp copay", "primary copay"],
        "copay_specialist": ["specialist copay", "specialist visit copay"],
        "copay_urgent_care": ["urgent care copay", "urgent care"],
        "copay_er": ["emergency room copay", "er copay", "emergency care"],
        "copay_generic_rx": ["generic drug copay", "generic rx", "tier 1 copay"],
        "copay_brand_rx": ["brand drug copay", "brand rx", "tier 2 copay"],
        "out_of_pocket_max_individual": [
            "individual out-of-pocket max",
            "individual oop max",
            "out-of-pocket maximum individual",
        ],
        "out_of_pocket_max_family": [
            "family out-of-pocket max",
            "family oop max",
            "out-of-pocket maximum family",
        ],
        "rx_deductible_amount": ["rx deductible", "prescription deductible"],
    }

    for field, keywords in mapping_money.items():
        value = _extract_money(text, keywords)
        if value is not None:
            values[field] = value
            extracted[field] = value

    coinsurance = _extract_percent(text, ["coinsurance", "member coinsurance"])
    if coinsurance is not None:
        values["coinsurance_percent"] = coinsurance
        extracted["coinsurance_percent"] = coinsurance

    plan_name = request.plan_name_hint
    if not plan_name:
        plan_name_match = re.search(r"plan\s+name\s*:\s*([^\n]+)", text, flags=re.IGNORECASE)
        if plan_name_match:
            plan_name = plan_name_match.group(1).strip()
    if not plan_name:
        plan_name = "Uploaded Insurance Plan"

    plan_type = _parse_plan_type(text)
    extracted["plan_type"] = plan_type.value

    rx_deductible_separate = bool(re.search(r"(separate|separately)\s+rx\s+deductible", text, flags=re.IGNORECASE))
    extracted["rx_deductible_separate"] = rx_deductible_separate

    covers_preventive = _extract_bool_preventive(text)
    extracted["covers_preventive_free"] = covers_preventive

    covered_services = _parse_service_list(text, "covered")
    excluded_services = _parse_service_list(text, "excluded")

    if not covered_services:
        covered_services = [
            "Preventive care",
            "Primary care visits",
            "Generic prescriptions",
            "Urgent care",
        ]
    if not excluded_services:
        excluded_services = ["Elective cosmetic procedures", "Out-of-network non-emergency care"]

    parsed_plan = InsurancePlan(
        plan_name=plan_name,
        plan_type=plan_type,
        monthly_premium=float(values["monthly_premium"]),
        annual_deductible_individual=float(values["annual_deductible_individual"]),
        annual_deductible_family=float(values["annual_deductible_family"]),
        copay_primary=float(values["copay_primary"]),
        copay_specialist=float(values["copay_specialist"]),
        copay_urgent_care=float(values["copay_urgent_care"]),
        copay_er=float(values["copay_er"]),
        copay_generic_rx=float(values["copay_generic_rx"]),
        copay_brand_rx=float(values["copay_brand_rx"]),
        coinsurance_percent=float(values["coinsurance_percent"]),
        out_of_pocket_max_individual=float(values["out_of_pocket_max_individual"]),
        out_of_pocket_max_family=float(values["out_of_pocket_max_family"]),
        covers_preventive_free=covers_preventive,
        rx_deductible_separate=rx_deductible_separate,
        rx_deductible_amount=float(values.get("rx_deductible_amount", 0)) if rx_deductible_separate else None,
    )

    confidence = round(min(len(extracted) / 12, 1.0), 2)
    summary = (
        f"Parsed {plan_name} with {confidence * 100:.0f}% confidence. "
        f"Estimated deductible ${parsed_plan.annual_deductible_individual:,.0f}, "
        f"OOP max ${parsed_plan.out_of_pocket_max_individual:,.0f}, "
        f"coinsurance {parsed_plan.coinsurance_percent:.0f}%."
    )

    return InsuranceUploadResult(
        parsed_plan=parsed_plan,
        confidence=confidence,
        covered_services=covered_services,
        excluded_services=excluded_services,
        summary=summary,
        extracted_fields=extracted,
    )
