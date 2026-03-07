import hashlib
import json
from pathlib import Path
from app.utils.http_client import get_client
from app.schemas.provider import Provider, ProviderDetail, ProcedurePrice, Address

DATA_DIR = Path(__file__).parent.parent / "data"
_cpt_codes: list[dict] = []
_mock_providers: list[dict] = []


def _load_cpt_codes() -> list[dict]:
    global _cpt_codes
    if not _cpt_codes:
        try:
            with open(DATA_DIR / "cpt_codes.json", encoding="utf-8") as f:
                data = json.load(f)
                _cpt_codes = data if isinstance(data, list) else []
        except (FileNotFoundError, json.JSONDecodeError):
            _cpt_codes = []
    return _cpt_codes


def _load_mock_providers() -> list[dict]:
    global _mock_providers
    if not _mock_providers:
        try:
            with open(DATA_DIR / "mock_providers.json", encoding="utf-8") as f:
                data = json.load(f)
                _mock_providers = data if isinstance(data, list) else []
        except (FileNotFoundError, json.JSONDecodeError):
            _mock_providers = []
    return _mock_providers


def _filter_mock_providers(
    query: str, zip_code: str, provider_type: str, limit: int
) -> list[Provider]:
    providers = _load_mock_providers()
    query_lower = query.lower().strip()
    zip_prefix = zip_code[:3] if zip_code else ""

    results: list[Provider] = []
    for item in providers:
        name = str(item.get("name", ""))
        specialty = str(item.get("specialty", ""))
        address = item.get("address", {})
        item_zip = str(address.get("zip", ""))
        item_type = str(item.get("provider_type", ""))

        if provider_type and provider_type != item_type:
            continue
        if query_lower and query_lower not in name.lower() and query_lower not in specialty.lower():
            continue
        if zip_prefix and not item_zip.startswith(zip_prefix):
            continue

        results.append(
            Provider(
                npi=str(item.get("npi", "")),
                name=name,
                provider_type=item_type,
                specialty=specialty or "General Practice",
                facility_type=str(item.get("facility_type", "clinic")),
                address=Address(
                    street=str(address.get("street", "")),
                    city=str(address.get("city", "")),
                    state=str(address.get("state", "")),
                    zip=item_zip,
                ),
                phone=str(item.get("phone", "")),
                accepts_medicaid=bool(item.get("accepts_medicaid", False)),
                accepts_medicare=bool(item.get("accepts_medicare", False)),
                sliding_scale=bool(item.get("sliding_scale", False)),
                distance_miles=float(item.get("distance_miles", 0)) if item.get("distance_miles") is not None else None,
            )
        )

    return results[:limit]


def _npi_hash_price(npi: str, base_low: float, base_high: float) -> float:
    """Generate a deterministic price from NPI hash within a range."""
    h = int(hashlib.md5(npi.encode()).hexdigest()[:8], 16)
    ratio = (h % 1000) / 1000.0
    return round(base_low + ratio * (base_high - base_low), 2)


def _parse_nppes_result(result: dict) -> Provider:
    """Parse a single NPPES API result into our Provider model."""
    basic = result.get("basic", {})
    addresses = result.get("addresses", [{}])
    practice = addresses[0] if addresses else {}
    taxonomies = result.get("taxonomies", [{}])
    taxonomy = taxonomies[0] if taxonomies else {}

    entity_type = result.get("enumeration_type", "")
    is_org = entity_type == "NPI-2"

    if is_org:
        name = basic.get("organization_name", "Unknown Organization")
    else:
        first = basic.get("first_name", "")
        last = basic.get("last_name", "")
        credential = basic.get("credential", "")
        name = f"{first} {last}"
        if credential:
            name += f", {credential}"

    specialty = taxonomy.get("desc", "General Practice")

    facility_map = {
        "urgent care": "urgent_care",
        "family": "clinic",
        "internal medicine": "clinic",
        "hospital": "hospital",
        "emergency": "er",
    }
    facility_type = "clinic"
    for key, val in facility_map.items():
        if key in specialty.lower():
            facility_type = val
            break

    return Provider(
        npi=result.get("number", ""),
        name=name.strip(),
        provider_type="organization" if is_org else "individual",
        specialty=specialty,
        facility_type=facility_type,
        address=Address(
            street=practice.get("address_1", ""),
            city=practice.get("city", ""),
            state=practice.get("state", ""),
            zip=practice.get("postal_code", "")[:5],
        ),
        phone=practice.get("telephone_number", ""),
        accepts_medicaid=True,
        accepts_medicare=True,
        sliding_scale=False,
    )


async def search_providers(
    query: str,
    zip_code: str = "",
    radius: int = 25,
    provider_type: str = "",
    limit: int = 20,
) -> list[Provider]:
    """Search NPPES NPI Registry for providers."""
    client = await get_client()
    try:
        params = {
            "version": "2.1",
            "taxonomy_description": query or "family medicine",
            "limit": min(limit, 200),
        }
        if zip_code:
            params["postal_code"] = zip_code
            params["radius"] = str(radius)
        if provider_type == "individual":
            params["enumeration_type"] = "NPI-1"
        elif provider_type == "organization":
            params["enumeration_type"] = "NPI-2"

        resp = await client.get(
            "https://npiregistry.cms.hhs.gov/api/",
            params=params,
        )
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            parsed = [_parse_nppes_result(r) for r in results[:limit]]
            if parsed:
                return parsed
    except Exception:
        pass

    return _filter_mock_providers(query, zip_code, provider_type, limit)


async def get_provider_by_npi(npi: str) -> Provider | None:
    """Fetch provider by NPI from NPPES, fallback to local mock dataset."""
    client = await get_client()
    try:
        resp = await client.get(
            "https://npiregistry.cms.hhs.gov/api/",
            params={"version": "2.1", "number": npi},
        )
        if resp.status_code == 200:
            data = resp.json()
            results_data = data.get("results", [])
            if results_data:
                return _parse_nppes_result(results_data[0])
    except Exception:
        pass

    for item in _load_mock_providers():
        if str(item.get("npi", "")) != npi:
            continue
        address = item.get("address", {})
        return Provider(
            npi=npi,
            name=str(item.get("name", "")),
            provider_type=str(item.get("provider_type", "organization")),
            specialty=str(item.get("specialty", "General Practice")),
            facility_type=str(item.get("facility_type", "clinic")),
            address=Address(
                street=str(address.get("street", "")),
                city=str(address.get("city", "")),
                state=str(address.get("state", "")),
                zip=str(address.get("zip", "")),
            ),
            phone=str(item.get("phone", "")),
            accepts_medicaid=bool(item.get("accepts_medicaid", False)),
            accepts_medicare=bool(item.get("accepts_medicare", False)),
            sliding_scale=bool(item.get("sliding_scale", False)),
            distance_miles=float(item.get("distance_miles", 0.0))
            if item.get("distance_miles") is not None
            else None,
        )
    return None


def get_provider_detail(npi: str, provider: Provider) -> ProviderDetail:
    """Enrich a provider with mock procedure pricing."""
    cpt_codes = _load_cpt_codes()
    procedure_prices = []

    for cpt in cpt_codes[:10]:
        code = str(cpt.get("cpt_code", ""))
        if not code:
            continue
        cash = _npi_hash_price(
            npi + code,
            float(cpt.get("typical_cash_price_low", 50)),
            float(cpt.get("typical_cash_price_high", 500)),
        )
        medicare = cpt.get("medicare_rate", 0)
        insured = round(cash * 0.6, 2) if cash else None

        procedure_prices.append(ProcedurePrice(
            cpt_code=code,
            procedure_name=str(cpt.get("procedure_name", "Healthcare Service")),
            cash_price=cash,
            medicare_rate=medicare,
            estimated_insured_price=insured,
            price_range_low=float(cpt.get("typical_cash_price_low", 50)),
            price_range_high=float(cpt.get("typical_cash_price_high", 500)),
        ))

    if not procedure_prices:
        procedure_prices.append(ProcedurePrice(
            cpt_code="99213",
            procedure_name="Office Visit",
            cash_price=_npi_hash_price(npi + "99213", 90, 220),
            medicare_rate=100,
            estimated_insured_price=_npi_hash_price(npi + "99213insured", 40, 140),
            price_range_low=90,
            price_range_high=220,
        ))

    return ProviderDetail(
        **provider.model_dump(),
        procedure_prices=procedure_prices,
        hours="Mon-Fri 8:00 AM - 5:00 PM",
        website=None,
        rating=round(3.5 + (_npi_hash_price(npi, 0, 15) / 10), 1),
    )
