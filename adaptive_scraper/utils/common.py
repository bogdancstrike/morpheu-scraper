from __future__ import annotations

import hashlib
import random
import re
import time
from typing import Any, Iterable, List, Optional
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import tldextract

TRACKING_PARAMS_PREFIXES = ("utm_", "fbclid", "gclid", "mc_", "oly_", "ref", "source", "cmp", "campaign")


def now_epoch() -> int:
    return int(time.time())


def clean_text(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    return text or None


def safe_json_loads(raw: str) -> Optional[Any]:
    import json
    try:
        return json.loads(raw)
    except Exception:
        return None


def safe_int(value: Any) -> Optional[int]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    s = str(value).strip()
    if not s:
        return None
    s = re.sub(r"(?<=\d)[\.,](?=\d{3}(\D|$))", "", s)
    match = re.search(r"-?\d+", s)
    if not match:
        return None
    try:
        return int(match.group(0))
    except Exception:
        return None


def maybe_list(value: Any) -> Optional[List[str]]:
    if value is None:
        return None
    if isinstance(value, list):
        vals = [str(v).strip() for v in value if str(v).strip()]
        return vals or None
    if isinstance(value, str):
        v = value.strip()
        return [v] if v else None
    return None


def count_words(text: Optional[str]) -> Optional[int]:
    return len(text.split()) if text else None


def estimate_reading_time_minutes(text: Optional[str]) -> Optional[int]:
    wc = count_words(text)
    return max(1, round(wc / 200)) if wc else None


def slugify(value: str, max_len: int = 80) -> str:
    value = value.lower()
    value = re.sub(r"https?://", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value[:max_len] or "item"


def dedupe_preserve_order(items: Iterable[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def canonicalize_url(url: str) -> str:
    parsed = urlparse(normalize_url(url))
    query_pairs = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if not any(k.lower().startswith(prefix) for prefix in TRACKING_PARAMS_PREFIXES)
    ]
    clean_query = urlencode(query_pairs, doseq=True)
    path = re.sub(r"/+", "/", parsed.path or "/")
    rebuilt = parsed._replace(query=clean_query, fragment="", path=path)
    final = urlunparse(rebuilt)
    return final.rstrip("/") if path != "/" else final


def domain_from_url(url: str) -> str:
    ext = tldextract.extract(normalize_url(url))
    if ext.suffix:
        return ".".join(part for part in [ext.domain, ext.suffix] if part)
    return urlparse(url).netloc.lower().removeprefix("www.")


def is_same_domain(url: str, domain: str) -> bool:
    try:
        return domain_from_url(url) == domain
    except Exception:
        return False


def path_from_url(url: str) -> str:
    return urlparse(url).path or "/"


def looks_like_article_url(url: str, domain: str) -> bool:
    if not url or not is_same_domain(url, domain):
        return False
    path = path_from_url(url).strip("/")
    if not path:
        return False
    lower = path.lower()
    bad = ["login", "cont", "abonare", "newsletter", "cookie", "privacy", "terms", "contact", "despre", "publicitate", "video", "foto", "/tag/", "/category/", "/autor/", "/authors/"]
    if any(fragment in lower for fragment in bad):
        return False
    if re.search(r"/20\d{2}/\d{1,2}/\d{1,2}/", lower):
        return True
    if lower.count("/") >= 1 or re.search(r"\d{2,}", lower) or len(lower) > 24:
        return True
    return False


def article_fingerprint(title: Optional[str], content: Optional[str], posted_date: Optional[str], source: Optional[str]) -> str:
    raw = "||".join([
        clean_text(title or "") or "",
        clean_text((content or "")[:500]) or "",
        clean_text(posted_date or "") or "",
        clean_text(source or "") or "",
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def add_jitter(min_ms: int, max_ms: int) -> None:
    if max_ms <= 0:
        return
    delay_ms = random.randint(max(0, min_ms), max(min_ms, max_ms))
    time.sleep(delay_ms / 1000)


def absolute_url(base_url: str, candidate: str | None) -> str | None:
    return urljoin(base_url, candidate) if candidate else None
