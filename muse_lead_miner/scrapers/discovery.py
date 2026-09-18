from typing import Any, Dict, List

from muse_lead_miner.scrapers.search import search_results_for


def generate_search_queries(country: str, region: str, city: str, niche: str) -> List[str]:
    base = niche.strip()
    items = [
        f'{base} {city} {country}',
        f'{base} {city}',
        f'{base} {city} {region}' if region else f'{base} {city}',
        f'{base} near {city}',
        f'{base} {country}',
    ]
    seen = set()
    unique = []
    for item in items:
        if item and item.lower() not in seen:
            seen.add(item.lower())
            unique.append(item)
    return unique


def discovery_source(country: str, region: str, city: str, niche: str, limit: int = 20) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for query in generate_search_queries(country, region, city, niche):
        for item in search_results_for(query, country=country, city=city, limit=limit):
            results.append(item)
    return results[:limit]
