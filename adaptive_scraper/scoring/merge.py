from __future__ import annotations
from typing import Any, Iterable, Tuple
PRIORITY = {
    "title": [("jsonld", 0.98), ("trafilatura", 0.92), ("extruct", 0.9), ("og", 0.82), ("fallback_card", 0.7), ("readability", 0.65)],
    "author": [("jsonld", 0.95), ("trafilatura", 0.88), ("extruct", 0.84), ("og", 0.75), ("fallback_card", 0.65)],
    "posted_date": [("jsonld", 0.95), ("htmldate", 0.9), ("trafilatura", 0.86), ("extruct", 0.8), ("og", 0.72), ("fallback_card", 0.6)],
    "updated_date": [("jsonld", 0.92), ("extruct", 0.85), ("og", 0.75), ("fallback_card", 0.6)],
    "summary": [("jsonld", 0.9), ("trafilatura", 0.86), ("extruct", 0.82), ("og", 0.78), ("fallback_card", 0.65)],
    "content": [("trafilatura", 0.95), ("dom", 0.85), ("api", 0.78)],
    "canonical_url": [("jsonld", 0.95), ("extruct", 0.9), ("canonical", 0.88), ("og", 0.8)],
}

def pick_field(field: str, candidates: Iterable[Tuple[str, Any]]) -> tuple[Any, str | None, float]:
    options = dict(candidates)
    for source, confidence in PRIORITY.get(field, []):
        value = options.get(source)
        if value not in (None, "", [], {}):
            return value, source, confidence
    for source, value in candidates:
        if value not in (None, "", [], {}):
            return value, source, 0.5
    return None, None, 0.0
