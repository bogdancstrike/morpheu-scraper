from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv()


def env_str(name: str, default: str) -> str:
    return os.getenv(name, default)


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


USER_AGENT = env_str(
    "USER_AGENT",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
)
OUTPUT_DIR = Path(env_str("OUTPUT_DIR", "output"))
CONFIG_FILE = Path(env_str("CONFIG_FILE", "discovered_sites.json"))
SCRAPED_CACHE_FILE = Path(env_str("SCRAPED_CACHE_FILE", "scraped_articles_cache.json"))
HEADLESS = env_bool("HEADLESS", True)
REQUEST_TIMEOUT = env_int("REQUEST_TIMEOUT", 25)
REQUEST_VERIFY_SSL = env_bool("REQUEST_VERIFY_SSL", False)
REQUEST_ALLOW_REDIRECTS = env_bool("REQUEST_ALLOW_REDIRECTS", True)
PLAYWRIGHT_TIMEOUT_MS = env_int("PLAYWRIGHT_TIMEOUT_MS", 30000)
PLAYWRIGHT_NETWORK_IDLE_TIMEOUT_MS = env_int("PLAYWRIGHT_NETWORK_IDLE_TIMEOUT_MS", 6000)
PLAYWRIGHT_PAGE_WAIT_AFTER_LOAD_MS = env_int("PLAYWRIGHT_PAGE_WAIT_AFTER_LOAD_MS", 1200)
USE_INFINITE_SCROLL = env_bool("USE_INFINITE_SCROLL", True)
SCROLL_ROUNDS = env_int("SCROLL_ROUNDS", 8)
SCROLL_WAIT_MS = env_int("SCROLL_WAIT_MS", 1800)
SCROLL_STABLE_ROUNDS_TO_STOP = env_int("SCROLL_STABLE_ROUNDS_TO_STOP", 2)
DEFAULT_MAX_ARTICLES = env_int("DEFAULT_MAX_ARTICLES", 50)
FOLLOW_ARTICLE_LINKS = env_bool("FOLLOW_ARTICLE_LINKS", True)
MIN_ARTICLE_WORDS = env_int("MIN_ARTICLE_WORDS", 120)
MIN_TITLE_LENGTH = env_int("MIN_TITLE_LENGTH", 18)
MAX_ANCHORS_TO_SCAN = env_int("MAX_ANCHORS_TO_SCAN", 1200)
MAX_CARDS_FROM_PAGE = env_int("MAX_CARDS_FROM_PAGE", 500)
MAX_API_PATTERNS = env_int("MAX_API_PATTERNS", 25)
RESCRAPE_ALWAYS = env_bool("RESCRAPE_ALWAYS", False)
CACHE_BY_CANONICAL_URL = env_bool("CACHE_BY_CANONICAL_URL", True)
DEFAULT_METHOD = env_str("DEFAULT_METHOD", "auto")
DEFAULT_PAGE_TYPE = env_str("DEFAULT_PAGE_TYPE", "auto")
SAVE_DEBUG_HTML = env_bool("SAVE_DEBUG_HTML", True)
SAVE_DEBUG_API_PAYLOADS = env_bool("SAVE_DEBUG_API_PAYLOADS", True)
MAX_DEBUG_API_PAYLOADS = env_int("MAX_DEBUG_API_PAYLOADS", 20)
HTTP_CLIENT = env_str("HTTP_CLIENT", "curl_cffi").strip().lower()
CURL_CFFI_IMPERSONATE = env_str("CURL_CFFI_IMPERSONATE", "chrome124")
CURL_CFFI_TIMEOUT = env_int("CURL_CFFI_TIMEOUT", 25)
USE_EXTRUCT = env_bool("USE_EXTRUCT", True)
USE_READABILITY = env_bool("USE_READABILITY", True)
USE_HTMLDATE = env_bool("USE_HTMLDATE", True)
USE_SELECTOLAX = env_bool("USE_SELECTOLAX", True)
BLOCK_NON_ESSENTIAL_RESOURCES = env_bool("BLOCK_NON_ESSENTIAL_RESOURCES", True)
BROWSER_PERSIST_STORAGE = env_bool("BROWSER_PERSIST_STORAGE", False)
PLAYWRIGHT_STORAGE_STATE_PATH = env_str("PLAYWRIGHT_STORAGE_STATE_PATH", "playwright_storage_state.json")
USE_STEALTH_HEADERS = env_bool("USE_STEALTH_HEADERS", True)
ANTI_BOT_JITTER_MIN_MS = env_int("ANTI_BOT_JITTER_MIN_MS", 150)
ANTI_BOT_JITTER_MAX_MS = env_int("ANTI_BOT_JITTER_MAX_MS", 750)
DOMAIN_COOLDOWN_SECONDS = env_int("DOMAIN_COOLDOWN_SECONDS", 0)
MAX_RETRIES_STATIC = env_int("MAX_RETRIES_STATIC", 2)
MAX_RETRIES_BROWSER = env_int("MAX_RETRIES_BROWSER", 1)
KEEP_INLINE_LINKS = env_bool("KEEP_INLINE_LINKS", False)
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


@dataclass
class SiteStats:
    total_runs: int = 0
    extraction_successes: int = 0
    extraction_failures: int = 0
    avg_article_word_count: float = 0.0
    avg_latency_ms: float = 0.0
    browser_successes: int = 0
    static_successes: int = 0
    api_discovery_successes: int = 0
    recent_status_codes: List[int] = field(default_factory=list)
    recent_block_signals: List[str] = field(default_factory=list)


@dataclass
class SiteConfig:
    method: str = DEFAULT_METHOD
    page_type: str = DEFAULT_PAGE_TYPE
    use_browser: bool = False
    use_api_intercept: bool = False
    use_infinite_scroll: bool = USE_INFINITE_SCROLL
    scroll_rounds: int = SCROLL_ROUNDS
    scroll_wait_ms: int = SCROLL_WAIT_MS
    max_articles: int = DEFAULT_MAX_ARTICLES
    discovered_at: int = 0
    last_success_at: int = 0
    notes: str | None = None
    api_patterns: list[str] = field(default_factory=list)
    article_url_patterns: list[str] = field(default_factory=list)
    listing_selectors: list[str] = field(default_factory=list)
    article_container_selectors: list[str] = field(default_factory=list)
    follow_article_links: bool = FOLLOW_ARTICLE_LINKS
    preferred_comment_selector: str | None = None
    hydration_keys: list[str] = field(default_factory=list)
    waf_signals: list[str] = field(default_factory=list)
    stats: SiteStats = field(default_factory=SiteStats)
