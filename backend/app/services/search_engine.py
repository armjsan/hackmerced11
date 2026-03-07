from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.calculator import ServiceType
from app.schemas.insurance import InsurancePlan
from app.schemas.medicine import Drug
from app.schemas.provider import ProcedurePrice
from app.schemas.search import (
    ConfidenceLevel,
    MedicineAlternative,
    MedicineFocus,
    RankedCostOption,
    UnifiedSearchRequest,
    UnifiedSearchResponse,
    UnifiedSearchSummary,
)
from app.services.benefits_engine import (
    check_eligibility,
    compute_fpl_percentage,
    estimate_annual_benefit_subsidy,
)
from app.services.drug_pricing import get_drug_price_comparison
from app.services.drug_search import search_drugs
from app.services.provider_search import get_provider_detail, search_providers

THERAPEUTIC_ALTERNATIVES: dict[str, list[str]] = {
    "metformin": ["glipizide", "empagliflozin"],
    "atorvastatin": ["simvastatin", "rosuvastatin"],
    "lisinopril": ["losartan", "amlodipine"],
    "levothyroxine": ["liothyronine"],
    "omeprazole": ["pantoprazole", "famotidine"],
    "amoxicillin": ["azithromycin", "doxycycline"],
    "albuterol": ["levalbuterol"],
    "insulin lispro": ["insulin aspart", "insulin glargine"],
}


@dataclass
class _OptionDraft:
    option_type: str
    name: str
    provider_name: str
    category: str
    location: str
    distance_miles: float | None
    list_price: float
    insured_estimate: float | None
    benefit_adjusted_cost: float
    confidence: ConfidenceLevel
    source: str
    network_status: str
    explanation: list[str]


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _guess_service_type(query: str) -> ServiceType:
    value = query.lower()
    if any(term in value for term in ["emergency", "er"]):
        return ServiceType.er
    if any(term in value for term in ["urgent", "walk-in"]):
        return ServiceType.urgent_care
    if any(term in value for term in ["x-ray", "xray", "mri", "ct", "imaging"]):
        return ServiceType.imaging
    if any(term in value for term in ["lab", "blood", "panel", "a1c"]):
        return ServiceType.lab
    if any(term in value for term in ["specialist", "cardiology", "dermatology"]):
        return ServiceType.specialist
    if any(term in value for term in ["physical", "preventive", "wellness"]):
        return ServiceType.preventive
    return ServiceType.office_visit


def _looks_like_service_query(query: str) -> bool:
    value = query.lower()
    return any(
        token in value
        for token in [
            "clinic",
            "doctor",
            "visit",
            "specialist",
            "xray",
            "x-ray",
            "mri",
            "ct",
            "lab",
            "urgent",
            "er",
            "emergency",
            "physical",
        ]
    )


def _copay_for_service(
    plan: InsurancePlan, service_type: ServiceType, is_generic_rx: bool
) -> float:
    if service_type == ServiceType.prescription:
        return plan.copay_generic_rx if is_generic_rx else plan.copay_brand_rx

    copay_map = {
        ServiceType.office_visit: plan.copay_primary,
        ServiceType.specialist: plan.copay_specialist,
        ServiceType.urgent_care: plan.copay_urgent_care,
        ServiceType.er: plan.copay_er,
        ServiceType.lab: plan.copay_specialist,
        ServiceType.imaging: plan.copay_specialist,
        ServiceType.preventive: 0,
        ServiceType.procedure: plan.copay_specialist,
    }
    return float(copay_map.get(service_type, plan.copay_primary))


def _estimate_member_cost(
    price: float,
    plan: InsurancePlan | None,
    service_type: ServiceType,
    deductible_progress: float,
    oop_progress: float,
    is_generic_rx: bool = True,
) -> float | None:
    if plan is None:
        return None

    if service_type == ServiceType.preventive and plan.covers_preventive_free:
        return 0.0

    deductible_remaining = max(
        plan.annual_deductible_individual * (1 - deductible_progress), 0
    )
    oop_remaining = max(plan.out_of_pocket_max_individual * (1 - oop_progress), 0)

    if oop_remaining <= 0:
        return 0.0

    copay = _copay_for_service(plan, service_type, is_generic_rx)

    if deductible_remaining > 0:
        deductible_paid = min(price, deductible_remaining)
        after_deductible = max(price - deductible_paid, 0)
        coinsurance_paid = after_deductible * (plan.coinsurance_percent / 100)
        member_cost = deductible_paid + coinsurance_paid
    else:
        member_cost = min(copay, price) if copay > 0 else price * (plan.coinsurance_percent / 100)

    member_cost = min(member_cost, oop_remaining, price)
    return round(max(member_cost, 0), 2)


def _pick_best_procedure(procedures: list[ProcedurePrice], query: str) -> ProcedurePrice | None:
    if not procedures:
        return None

    query_lower = query.lower()
    for procedure in procedures:
        if query_lower in procedure.procedure_name.lower() or query_lower in procedure.cpt_code.lower():
            return procedure

    return min(procedures, key=lambda p: p.cash_price)


def _network_status(is_insured: bool, is_sliding_scale: bool, accepts_public: bool) -> str:
    if not is_insured:
        return "cash-pay"
    if accepts_public:
        return "public-coverage-friendly"
    if is_sliding_scale:
        return "sliding-scale"
    return "unknown"


def _confidence_penalty(level: ConfidenceLevel) -> float:
    if level == ConfidenceLevel.high:
        return 0.0
    if level == ConfidenceLevel.medium:
        return 0.5
    return 1.0


def _network_penalty(status: str) -> float:
    if status in {"cash-pay", "public-coverage-friendly", "sliding-scale"}:
        return 0.0
    return 0.7


def _option_type_penalty(option_type: str) -> float:
    return 0.0 if option_type == "medicine" else 1.0


def _estimate_lowest_drug_price(ndc: str, quantity: int, zip_code: str) -> float | None:
    comparison = get_drug_price_comparison(ndc=ndc, quantity=quantity, zip_code=zip_code)
    if not comparison:
        return None
    return round(comparison.lowest_price, 2)


async def _build_medicine_focus(
    medicine_matches: list[Drug], quantity: int, zip_code: str
) -> MedicineFocus:
    primary_match = medicine_matches[0] if medicine_matches else None
    if not primary_match:
        return MedicineFocus(primary_match=None, medicine_match_count=0, alternatives=[])

    seen_ndc = {primary_match.ndc}
    alternatives: list[MedicineAlternative] = []

    def add_alternative(drug: Drug, alternative_type: str, reason: str):
        if drug.ndc in seen_ndc:
            return
        seen_ndc.add(drug.ndc)
        alternatives.append(
            MedicineAlternative(
                drug=drug,
                alternative_type=alternative_type,
                reason=reason,
                estimated_lowest_price=_estimate_lowest_drug_price(
                    ndc=drug.ndc,
                    quantity=quantity,
                    zip_code=zip_code,
                ),
            )
        )

    primary_comparison = get_drug_price_comparison(
        ndc=primary_match.ndc,
        quantity=quantity,
        zip_code=zip_code,
    )
    if primary_comparison and primary_comparison.generic_alternative:
        add_alternative(
            primary_comparison.generic_alternative,
            "generic-equivalent",
            "Same active ingredient at potentially lower cost.",
        )

    same_generic = await search_drugs(primary_match.generic_name, limit=20)
    for candidate in same_generic.drugs:
        if candidate.generic_name.lower() != primary_match.generic_name.lower():
            continue
        alt_type = "same-generic"
        reason = "Alternative manufacturer/label with the same generic ingredient."
        add_alternative(candidate, alt_type, reason)
        if len(alternatives) >= 4:
            break

    therapy_keys = THERAPEUTIC_ALTERNATIVES.get(primary_match.generic_name.lower(), [])
    for alt_generic in therapy_keys:
        therapy_results = await search_drugs(alt_generic, limit=5)
        if not therapy_results.drugs:
            continue

        candidate = therapy_results.drugs[0]
        add_alternative(
            candidate,
            "therapeutic-alternative",
            "Different medicine used for similar treatment goals; confirm with a clinician.",
        )

    alternatives.sort(
        key=lambda alt: alt.estimated_lowest_price
        if alt.estimated_lowest_price is not None
        else 999999
    )

    return MedicineFocus(
        primary_match=primary_match,
        medicine_match_count=len(medicine_matches),
        alternatives=alternatives[:8],
    )


def _rank_options(drafts: list[_OptionDraft], max_results: int) -> list[RankedCostOption]:
    if not drafts:
        return []

    max_cost = max((item.benefit_adjusted_cost for item in drafts), default=1) or 1
    ranked: list[RankedCostOption] = []

    for index, item in enumerate(drafts):
        distance = item.distance_miles if item.distance_miles is not None else 5.0
        normalized_cost = min(item.benefit_adjusted_cost / max_cost, 1)
        distance_penalty = min(distance / 25.0, 1)
        conf_penalty = _confidence_penalty(item.confidence)
        network_penalty = _network_penalty(item.network_status)
        type_penalty = _option_type_penalty(item.option_type)

        rank_score = (
            0.63 * normalized_cost
            + 0.12 * distance_penalty
            + 0.10 * conf_penalty
            + 0.05 * network_penalty
            + 0.10 * type_penalty
        )

        ranked.append(
            RankedCostOption(
                option_id=f"{item.option_type}-{index}-{_slug(item.provider_name)}",
                option_type=item.option_type,
                name=item.name,
                provider_name=item.provider_name,
                category=item.category,
                location=item.location,
                distance_miles=item.distance_miles,
                list_price=round(item.list_price, 2),
                insured_estimate=item.insured_estimate,
                benefit_adjusted_cost=round(item.benefit_adjusted_cost, 2),
                confidence=item.confidence,
                source=item.source,
                network_status=item.network_status,
                rank_score=round(rank_score, 4),
                explanation=item.explanation,
            )
        )

    ranked.sort(key=lambda item: item.rank_score)
    return ranked[:max_results]


async def run_unified_search(request: UnifiedSearchRequest) -> UnifiedSearchResponse:
    query = request.query.strip()
    household = request.household
    service_type = _guess_service_type(query)

    eligible_programs = check_eligibility(household)
    fpl_percentage = compute_fpl_percentage(household.annual_income, household.household_size)
    annual_subsidy = estimate_annual_benefit_subsidy(
        annual_income=household.annual_income,
        household_size=household.household_size,
        program_count=len(eligible_programs),
    )

    medicine_offset = annual_subsidy / 12
    provider_offset = annual_subsidy / 10

    drafts: list[_OptionDraft] = []
    medicine_matches: list[Drug] = []

    if request.include_medicines:
        drug_results = await search_drugs(query, limit=12)
        medicine_matches = drug_results.drugs

        for drug in drug_results.drugs[:5]:
            comparison = get_drug_price_comparison(
                ndc=drug.ndc,
                quantity=request.quantity,
                zip_code=request.zip_code,
            )
            if not comparison:
                continue

            for price in comparison.pharmacy_prices[:6]:
                insured_estimate = _estimate_member_cost(
                    price=price.price,
                    plan=request.insurance_plan,
                    service_type=ServiceType.prescription,
                    deductible_progress=request.deductible_progress,
                    oop_progress=request.oop_progress,
                    is_generic_rx=drug.is_generic,
                )
                base_cost = insured_estimate if insured_estimate is not None else price.price
                benefit_adjusted = max(base_cost - medicine_offset, 0)

                explanation = [
                    f"Cash price from {price.pharmacy_name}: ${price.price:.2f}",
                    f"Estimated benefit offset applied: ${medicine_offset:.2f}",
                ]
                if insured_estimate is not None:
                    explanation.append(
                        f"Insurance estimate (optional): ${insured_estimate:.2f}"
                    )
                if comparison.generic_alternative and not drug.is_generic:
                    explanation.append(
                        f"Generic option exists: {comparison.generic_alternative.brand_name}"
                    )
                if price.with_coupon and price.coupon_name:
                    explanation.append(f"Coupon available: {price.coupon_name}")

                drafts.append(
                    _OptionDraft(
                        option_type="medicine",
                        name=f"{drug.brand_name} ({drug.generic_name}) {drug.strength}".strip(),
                        provider_name=price.pharmacy_name,
                        category="medicine",
                        location=(
                            "Online / mail delivery"
                            if price.pharmacy_type in {"online", "mail_order"}
                            else f"Near ZIP {request.zip_code}" if request.zip_code else "Nearby"
                        ),
                        distance_miles=None
                        if price.pharmacy_type in {"online", "mail_order"}
                        else 4.0,
                        list_price=price.price,
                        insured_estimate=insured_estimate,
                        benefit_adjusted_cost=benefit_adjusted,
                        confidence=ConfidenceLevel.high,
                        source="NADAC-based pharmacy model",
                        network_status="cash-pay" if request.insurance_plan is None else "unknown",
                        explanation=explanation,
                    )
                )

    medicine_focus = await _build_medicine_focus(
        medicine_matches=medicine_matches,
        quantity=request.quantity,
        zip_code=request.zip_code,
    )

    include_provider_results = request.include_providers and (
        len(drafts) == 0 or _looks_like_service_query(query)
    )

    if include_provider_results:
        providers = await search_providers(
            query=query,
            zip_code=request.zip_code,
            radius=25,
            provider_type="",
            limit=max(6, request.max_results),
        )

        for provider in providers[:6]:
            detail = get_provider_detail(provider.npi, provider)
            procedure = _pick_best_procedure(detail.procedure_prices, query)
            if procedure is None:
                continue

            insured_estimate = _estimate_member_cost(
                price=procedure.cash_price,
                plan=request.insurance_plan,
                service_type=service_type,
                deductible_progress=request.deductible_progress,
                oop_progress=request.oop_progress,
            )
            base_cost = insured_estimate if insured_estimate is not None else procedure.cash_price
            benefit_adjusted = max(base_cost - provider_offset, 0)
            accepts_public = provider.accepts_medicaid or provider.accepts_medicare
            network_status = _network_status(
                is_insured=household.currently_insured,
                is_sliding_scale=provider.sliding_scale,
                accepts_public=accepts_public,
            )

            explanation = [
                f"Estimated cash price: ${procedure.cash_price:.2f} ({procedure.cpt_code})",
                f"Estimated benefit offset applied: ${provider_offset:.2f}",
            ]
            if insured_estimate is not None:
                explanation.append(
                    f"Insurance estimate (optional): ${insured_estimate:.2f}"
                )
            if provider.sliding_scale:
                explanation.append("Provider reports sliding-scale payment options")

            drafts.append(
                _OptionDraft(
                    option_type="provider_service",
                    name=procedure.procedure_name,
                    provider_name=provider.name,
                    category=provider.specialty,
                    location=f"{provider.address.city}, {provider.address.state} {provider.address.zip}",
                    distance_miles=provider.distance_miles,
                    list_price=procedure.cash_price,
                    insured_estimate=insured_estimate,
                    benefit_adjusted_cost=benefit_adjusted,
                    confidence=ConfidenceLevel.medium,
                    source="NPPES + synthetic CPT pricing",
                    network_status=network_status,
                    explanation=explanation,
                )
            )

    ranked_options = _rank_options(drafts, request.max_results)

    min_cash = min((option.list_price for option in ranked_options), default=None)
    insured_values = [
        option.insured_estimate
        for option in ranked_options
        if option.insured_estimate is not None
    ]
    min_insured = min(insured_values) if insured_values else None
    min_benefit_adjusted = min(
        (option.benefit_adjusted_cost for option in ranked_options), default=None
    )

    assumptions = [
        "Search prioritizes direct medicine matches and lower-cost generic/therapeutic alternatives.",
        "Insurance calculations are optional and only used when a plan is provided.",
        "Benefit offset is an estimate and not a guarantee of approval or payout.",
    ]

    summary = UnifiedSearchSummary(
        min_cash_price=round(min_cash, 2) if min_cash is not None else None,
        min_insured_price=round(min_insured, 2) if min_insured is not None else None,
        min_benefit_adjusted_price=round(min_benefit_adjusted, 2)
        if min_benefit_adjusted is not None
        else None,
        estimated_annual_benefit_subsidy=round(annual_subsidy, 2),
    )

    return UnifiedSearchResponse(
        query=query,
        zip_code=request.zip_code,
        fpl_percentage=fpl_percentage,
        medicine_focus=medicine_focus,
        eligible_programs=eligible_programs,
        ranked_options=ranked_options,
        summary=summary,
        assumptions=assumptions,
    )
