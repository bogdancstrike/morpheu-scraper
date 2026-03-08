from __future__ import annotations
import re
from typing import List, Tuple
from bs4 import BeautifulSoup
from adaptive_scraper.utils.common import safe_json_loads
PATTERNS = [("__NEXT_DATA__", r"__NEXT_DATA__\s*=\s*(\{.*?\})\s*;?"), ("__INITIAL_STATE__", r"__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;?"), ("__NUXT__", r"__NUXT__\s*=\s*(\{.*?\})\s*;?"), ("__APOLLO_STATE__", r"__APOLLO_STATE__\s*=\s*(\{.*?\})\s*;?"), ("__PRELOADED_STATE__", r"__PRELOADED_STATE__\s*=\s*(\{.*?\})\s*;?")]

def extract_hydration_data(soup: BeautifulSoup) -> Tuple[List[dict], List[str]]:
    results, keys = [], []
    for script in soup.find_all("script"):
        content = script.string or script.get_text(" ", strip=False)
        if not content:
            continue
        for key, pattern in PATTERNS:
            match = re.search(pattern, content, re.DOTALL)
            if not match:
                continue
            parsed = safe_json_loads(match.group(1))
            if isinstance(parsed, dict):
                results.append(parsed)
                keys.append(key)
    return results, keys
