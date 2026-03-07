import json
from pathlib import Path
from app.schemas.benefits import BenefitProgram, EligibilityInput, EligibilityResult, HealthCenter
from app.utils.http_client import get_client

DATA_DIR = Path(__file__).parent.parent / "data"
_programs: list[dict] = []

# 2024 HHS Federal Poverty Level guidelines (48 contiguous states + DC)
FPL_BASE = 15_060
FPL_PER_ADDITIONAL = 5_380


def _load_programs() -> list[dict]:
    global _programs
    if not _programs:
        try:
            with open(DATA_DIR / "benefit_programs.json", encoding="utf-8") as f:
                data = json.load(f)
                _programs = data if isinstance(data, list) else []
        except (FileNotFoundError, json.JSONDecodeError):
            _programs = []
    return _programs


def compute_fpl_percentage(annual_income: float, household_size: int) -> float:
    """Compute household income as percentage of Federal Poverty Level."""
    fpl_threshold = FPL_BASE + max(0, household_size - 1) * FPL_PER_ADDITIONAL
    if fpl_threshold == 0:
        return 0
    return round((annual_income / fpl_threshold) * 100, 1)


def check_eligibility(input_data: EligibilityInput) -> list[BenefitProgram]:
    """Match user against all benefit programs."""
    programs = _load_programs()
    fpl_pct = compute_fpl_percentage(input_data.annual_income, input_data.household_size)
    eligible = []

    for p in programs:
        # Check state
        states = p.get("states", ["ALL"])
        if states != ["ALL"] and input_data.state.upper() not in states:
            continue

        # Check income limit
        limit = p.get("income_limit_fpl_percent")
        if limit is not None and fpl_pct > limit:
            continue

        # Check age
        age_min = p.get("age_min")
        age_max = p.get("age_max")
        if age_min is not None and input_data.age < age_min:
            continue
        if age_max is not None and input_data.age > age_max:
            continue

        # Check special requirements
        if p.get("requires_children") and not input_data.has_children:
            continue
        if p.get("requires_disability") and not input_data.has_disability:
            continue
        if p.get("requires_pregnancy") and not input_data.is_pregnant:
            continue

        eligible.append(BenefitProgram(**p))

    return eligible


async def find_health_centers(zip_code: str, radius: int = 30) -> list[HealthCenter]:
    """Search HRSA for nearby Federally Qualified Health Centers."""
    if not zip_code:
        return []

    client = await get_client()
    try:
        resp = await client.get(
            "https://data.hrsa.gov/api/facility",
            params={
                "$filter": f"contains(Zip,'{zip_code[:3]}')",
                "$top": "10",
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            centers = []
            for item in data.get("value", [])[:10]:
                centers.append(HealthCenter(
                    name=item.get("Name", "Community Health Center"),
                    address=f"{item.get('Address', '')} {item.get('City', '')}, {item.get('State', '')} {item.get('Zip', '')}",
                    phone=item.get("Phone", ""),
                    distance_miles=5.0,
                    services=["Primary Care", "Dental", "Behavioral Health"],
                    sliding_scale=True,
                    website=item.get("Website", ""),
                ))
            return centers
    except Exception:
        pass

    # Fallback mock data
    return [
        HealthCenter(
            name="Community Health Center",
            address=f"Near {zip_code}",
            phone="(800) 555-0100",
            distance_miles=3.2,
            services=["Primary Care", "Dental", "Behavioral Health", "Pharmacy"],
            sliding_scale=True,
            website="https://findahealthcenter.hrsa.gov/",
        ),
    ]


async def get_eligibility_result(input_data: EligibilityInput) -> EligibilityResult:
    """Full eligibility check including nearby health centers."""
    fpl_pct = compute_fpl_percentage(input_data.annual_income, input_data.household_size)
    eligible = check_eligibility(input_data)
    centers = await find_health_centers(input_data.zip_code)

    count = len(eligible)
    if count == 0:
        summary = "Based on the information provided, we didn't find matching programs. You may still qualify for community health center services on a sliding scale."
    else:
        summary = f"You may qualify for {count} program{'s' if count != 1 else ''}! Your household income is {fpl_pct}% of the Federal Poverty Level."

    return EligibilityResult(
        eligible_programs=eligible,
        nearby_health_centers=centers,
        fpl_percentage=fpl_pct,
        summary=summary,
    )


def estimate_annual_benefit_subsidy(
    annual_income: float, household_size: int, program_count: int
) -> float:
    """
    Approximate annual subsidy value for transparency ranking.
    This is intentionally conservative for MVP and should be replaced by
    program-specific formulas in production.
    """
    if household_size <= 0:
        return 0.0

    fpl_pct = compute_fpl_percentage(annual_income, household_size)
    if program_count <= 0:
        return 0.0

    if fpl_pct <= 138:
        base = 1800
    elif fpl_pct <= 200:
        base = 1200
    elif fpl_pct <= 250:
        base = 800
    else:
        base = 350

    bonus = min(program_count * 120, 480)
    return float(round(base + bonus, 2))
