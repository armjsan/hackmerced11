import json
from pathlib import Path
from app.utils.http_client import get_client
from app.schemas.medicine import Drug, DrugSearchResponse

DATA_DIR = Path(__file__).parent.parent / "data"
_drug_cache: dict[str, list[Drug]] = {}
_local_drugs: list[dict] = []


def _load_local_drugs() -> list[dict]:
    global _local_drugs
    if not _local_drugs:
        try:
            with open(DATA_DIR / "common_drugs.json", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    _local_drugs = data
                else:
                    _local_drugs = []
        except (FileNotFoundError, json.JSONDecodeError):
            _local_drugs = []
    return _local_drugs


async def search_drugs_openfda(query: str, limit: int = 20) -> list[Drug]:
    """Search OpenFDA for drugs by name."""
    if query.lower() in _drug_cache:
        return _drug_cache[query.lower()][:limit]

    client = await get_client()
    try:
        search_term = f'(brand_name:"{query}"+generic_name:"{query}")'
        resp = await client.get(
            "https://api.fda.gov/drug/ndc.json",
            params={"search": search_term, "limit": min(limit, 100)},
        )
        if resp.status_code == 200:
            data = resp.json()
            drugs = []
            seen = set()
            for result in data.get("results", []):
                ndc = (result.get("product_ndc") or "").replace("-", "")
                if not ndc or ndc in seen:
                    continue
                seen.add(ndc)
                brand = result.get("brand_name", "")
                generic = result.get("generic_name", "")
                drugs.append(Drug(
                    ndc=result.get("product_ndc", ""),
                    brand_name=brand,
                    generic_name=generic,
                    dosage_form=result.get("dosage_form", "TABLET"),
                    strength=result.get("active_ingredients", [{}])[0].get("strength", "")
                    if result.get("active_ingredients") else "",
                    manufacturer=result.get("labeler_name", "Unknown"),
                    is_generic=brand.upper() == generic.upper(),
                    rx_required=result.get("product_type", "") == "HUMAN PRESCRIPTION DRUG",
                ))
            _drug_cache[query.lower()] = drugs
            return drugs[:limit]
    except Exception:
        pass

    return _search_local_drugs(query, limit)


def _search_local_drugs(query: str, limit: int = 20) -> list[Drug]:
    """Fallback: search local drug database."""
    drugs = _load_local_drugs()
    query_lower = query.lower()
    results = []
    for d in drugs:
        brand_name = str(d.get("brand_name", ""))
        generic_name = str(d.get("generic_name", ""))
        if query_lower in brand_name.lower() or query_lower in generic_name.lower():
            results.append(Drug(
                ndc=str(d.get("ndc", "")),
                brand_name=brand_name,
                generic_name=generic_name,
                dosage_form=str(d.get("dosage_form", "TABLET")),
                strength=str(d.get("strength", "")),
                manufacturer=str(d.get("manufacturer", "Unknown")),
                is_generic=bool(d.get("is_generic", False)),
                rx_required=bool(d.get("rx_required", True)),
            ))
    return results[:limit]


async def autocomplete_drugs(query: str, limit: int = 8) -> list[dict]:
    """Return autocomplete suggestions."""
    drugs = _load_local_drugs()
    query_lower = query.lower()
    results = []
    for d in drugs:
        brand_name = str(d.get("brand_name", ""))
        generic_name = str(d.get("generic_name", ""))
        if brand_name.lower().startswith(query_lower) or generic_name.lower().startswith(query_lower):
            results.append({
                "name": f"{brand_name} ({generic_name}) - {d.get('strength', '')}",
                "ndc": d.get("ndc", ""),
            })
    return results[:limit]


async def search_drugs(query: str, limit: int = 20) -> DrugSearchResponse:
    """Main search function: tries OpenFDA first, falls back to local."""
    drugs = await search_drugs_openfda(query, limit)
    if not drugs:
        drugs = _search_local_drugs(query, limit)
    return DrugSearchResponse(drugs=drugs, total_count=len(drugs), query=query)
