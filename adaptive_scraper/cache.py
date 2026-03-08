from __future__ import annotations
import json
from typing import Any, Dict, Optional
from adaptive_scraper.config import CACHE_BY_CANONICAL_URL, RESCRAPE_ALWAYS, SCRAPED_CACHE_FILE
from adaptive_scraper.models import ArticleRecord
from adaptive_scraper.utils.common import canonicalize_url, now_epoch

def load_scraped_cache() -> Dict[str, Dict[str, Any]]:
    if not SCRAPED_CACHE_FILE.exists():
        return {}
    try:
        return json.loads(SCRAPED_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_scraped_cache(cache: Dict[str, Dict[str, Any]]) -> None:
    SCRAPED_CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

def get_cache_key(record: ArticleRecord) -> Optional[str]:
    if CACHE_BY_CANONICAL_URL and record.metadata.canonical_url:
        return canonicalize_url(record.metadata.canonical_url)
    if record.article.url:
        return canonicalize_url(record.article.url)
    return None

def is_cached_url(domain: str, url: Optional[str], cache: Dict[str, Dict[str, Any]]) -> bool:
    if RESCRAPE_ALWAYS or not url:
        return False
    return canonicalize_url(url) in cache.get(domain, {})

def mark_cached(domain: str, record: ArticleRecord, cache: Dict[str, Dict[str, Any]], output_file: Optional[str] = None) -> None:
    key = get_cache_key(record)
    if not key:
        return
    cache.setdefault(domain, {})
    cache[domain][key] = {
        "url": record.article.url,
        "canonical_url": record.metadata.canonical_url,
        "title": record.article.title,
        "posted_date": record.article.posted_date,
        "author": record.article.author,
        "cached_at": now_epoch(),
        "output_file": output_file,
    }
    save_scraped_cache(cache)
