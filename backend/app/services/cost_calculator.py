from app.schemas.insurance import InsurancePlan
from app.schemas.calculator import (
    CostScenario, CostCalculationRequest, CostLineItem, CostCalculationResult,
    ServiceType,
)

# Pre-built common healthcare scenarios
DEFAULT_SCENARIOS = [
    CostScenario(service_type=ServiceType.office_visit, service_name="Primary Care Visit", retail_price=250, frequency=4),
    CostScenario(service_type=ServiceType.specialist, service_name="Specialist Visit", retail_price=400, frequency=2),
    CostScenario(service_type=ServiceType.urgent_care, service_name="Urgent Care Visit", retail_price=350, frequency=1),
    CostScenario(service_type=ServiceType.prescription, service_name="Generic Prescription (monthly)", retail_price=45, frequency=12),
    CostScenario(service_type=ServiceType.lab, service_name="Blood Work (CBC + CMP)", retail_price=200, frequency=2),
    CostScenario(service_type=ServiceType.preventive, service_name="Annual Physical", retail_price=300, frequency=1),
    CostScenario(service_type=ServiceType.imaging, service_name="X-Ray", retail_price=250, frequency=1),
    CostScenario(service_type=ServiceType.er, service_name="Emergency Room Visit", retail_price=2500, frequency=0),
    CostScenario(service_type=ServiceType.prescription, service_name="Brand Prescription (monthly)", retail_price=150, frequency=0),
]


def get_copay(plan: InsurancePlan, service_type: ServiceType) -> float:
    """Get the copay amount for a service type."""
    copay_map = {
        ServiceType.office_visit: plan.copay_primary,
        ServiceType.specialist: plan.copay_specialist,
        ServiceType.urgent_care: plan.copay_urgent_care,
        ServiceType.er: plan.copay_er,
        ServiceType.prescription: plan.copay_generic_rx,
        ServiceType.lab: plan.copay_specialist,
        ServiceType.imaging: plan.copay_specialist,
        ServiceType.preventive: 0,
        ServiceType.procedure: plan.copay_specialist,
    }
    return copay_map.get(service_type, plan.copay_primary)


def generate_recommendation(
    net_savings: float, annual_premiums: float, annual_retail: float
) -> str:
    """Generate a human-readable recommendation."""
    if annual_premiums == 0:
        return "You haven't entered premium costs. Add your monthly premium for a complete analysis."

    if net_savings > 0:
        ratio = net_savings / annual_premiums
        if ratio > 2:
            return f"Your insurance provides excellent value — for every $1 in premiums, you save ${ratio:.2f} compared to paying cash. Your plan is well-suited to your healthcare usage."
        elif ratio > 1:
            return f"Your insurance provides good value — you save ${net_savings:,.0f} annually compared to paying cash after accounting for premiums."
        else:
            return f"Your insurance provides moderate value. You save ${net_savings:,.0f}, but premiums consume a large share. Consider if a lower-premium plan might work if you're generally healthy."
    else:
        loss = abs(net_savings)
        return f"At your current usage level, you're paying ${loss:,.0f} more with insurance than you would paying cash. Consider a high-deductible plan with an HSA, or explore if you qualify for subsidies."


def compute_costs(request: CostCalculationRequest) -> CostCalculationResult:
    """Simulate a full insurance year and compute true costs."""
    plan = request.insurance_plan
    scenarios = request.scenarios

    deductible_remaining = plan.annual_deductible_individual
    rx_deductible_remaining = (
        plan.rx_deductible_amount if plan.rx_deductible_separate and plan.rx_deductible_amount else 0
    )
    oop_spent = 0.0
    oop_max = plan.out_of_pocket_max_individual

    line_items: list[CostLineItem] = []

    for scenario in scenarios:
        if scenario.frequency == 0:
            continue

        total_retail = 0.0
        total_insured = 0.0
        total_deductible = 0.0
        total_copay = 0.0
        total_coinsurance = 0.0
        total_insurance_paid = 0.0

        for _ in range(scenario.frequency):
            retail_price = scenario.retail_price
            total_retail += retail_price

            # OOP max reached — insurance pays everything
            if oop_spent >= oop_max:
                total_insurance_paid += retail_price
                continue

            # Preventive services covered at $0
            if scenario.service_type == ServiceType.preventive and plan.covers_preventive_free:
                total_insurance_paid += retail_price
                continue

            copay = get_copay(plan, scenario.service_type)
            member_pays = 0.0

            # Determine which deductible applies
            is_rx = scenario.service_type == ServiceType.prescription
            if is_rx and plan.rx_deductible_separate:
                ded_remaining = rx_deductible_remaining
            else:
                ded_remaining = deductible_remaining

            if ded_remaining > 0:
                # Deductible not yet met
                deductible_portion = min(retail_price, ded_remaining)
                member_pays += deductible_portion
                total_deductible += deductible_portion

                if is_rx and plan.rx_deductible_separate:
                    rx_deductible_remaining -= deductible_portion
                else:
                    deductible_remaining -= deductible_portion

                remaining = retail_price - deductible_portion
                if remaining > 0:
                    coinsurance_amount = remaining * (plan.coinsurance_percent / 100)
                    member_pays += coinsurance_amount
                    total_coinsurance += coinsurance_amount
            else:
                # Deductible met — apply copay or coinsurance
                if copay > 0:
                    member_pays = min(copay, retail_price)
                    total_copay += member_pays
                else:
                    coinsurance_amount = retail_price * (plan.coinsurance_percent / 100)
                    member_pays = coinsurance_amount
                    total_coinsurance += coinsurance_amount

            # Cap at OOP max
            if oop_spent + member_pays > oop_max:
                member_pays = max(0, oop_max - oop_spent)

            oop_spent += member_pays
            insurance_pays = retail_price - member_pays
            total_insured += member_pays
            total_insurance_paid += insurance_pays

        line_items.append(CostLineItem(
            service_name=scenario.service_name,
            retail_price=scenario.retail_price,
            frequency=scenario.frequency,
            annual_retail_cost=round(total_retail, 2),
            annual_insured_cost=round(total_insured, 2),
            deductible_applied=round(total_deductible, 2),
            copay_applied=round(total_copay, 2),
            coinsurance_applied=round(total_coinsurance, 2),
            insurance_paid=round(total_insurance_paid, 2),
            savings=round(total_retail - total_insured, 2),
        ))

    annual_premiums = plan.monthly_premium * 12
    annual_retail_total = sum(li.annual_retail_cost for li in line_items)
    annual_insured_oop = sum(li.annual_insured_cost for li in line_items)
    annual_insurance_pays = sum(li.insurance_paid for li in line_items)
    total_true_cost = annual_premiums + annual_insured_oop
    net_savings = annual_retail_total - total_true_cost

    totals = {
        "annual_premiums": round(annual_premiums, 2),
        "annual_retail_total": round(annual_retail_total, 2),
        "annual_insured_total": round(annual_insured_oop, 2),
        "annual_insurance_pays": round(annual_insurance_pays, 2),
        "deductible_used": round(plan.annual_deductible_individual - deductible_remaining, 2),
        "deductible_remaining": round(deductible_remaining, 2),
        "oop_max_remaining": round(max(0, oop_max - oop_spent), 2),
        "total_true_cost_insured": round(total_true_cost, 2),
        "net_savings": round(net_savings, 2),
        "insurance_value_ratio": round(net_savings / annual_premiums, 2) if annual_premiums > 0 else 0,
    }

    recommendation = generate_recommendation(net_savings, annual_premiums, annual_retail_total)

    return CostCalculationResult(
        line_items=line_items,
        totals=totals,
        recommendation=recommendation,
    )


def get_default_scenarios() -> list[CostScenario]:
    return DEFAULT_SCENARIOS
