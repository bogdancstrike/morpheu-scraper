from __future__ import annotations
import time, requests
from curl_cffi import requests as curl_requests
from adaptive_scraper.config import CURL_CFFI_IMPERSONATE, CURL_CFFI_TIMEOUT, HTTP_CLIENT, MAX_RETRIES_STATIC, REQUEST_ALLOW_REDIRECTS, REQUEST_TIMEOUT, REQUEST_VERIFY_SSL, USER_AGENT, USE_STEALTH_HEADERS, ANTI_BOT_JITTER_MIN_MS, ANTI_BOT_JITTER_MAX_MS
from adaptive_scraper.detectors.anti_bot import detect_block_signals
from adaptive_scraper.models import FetchResult
from adaptive_scraper.utils.common import add_jitter
DEFAULT_HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8", "Cache-Control": "no-cache", "Pragma": "no-cache"}
if USE_STEALTH_HEADERS: DEFAULT_HEADERS.update({"Upgrade-Insecure-Requests": "1", "Sec-Fetch-Site": "none", "Sec-Fetch-Mode": "navigate", "Sec-Fetch-User": "?1", "Sec-Fetch-Dest": "document"})
def fetch_static(url: str) -> FetchResult:
    last_exc = None
    for _ in range(MAX_RETRIES_STATIC + 1):
        add_jitter(ANTI_BOT_JITTER_MIN_MS, ANTI_BOT_JITTER_MAX_MS); started = time.time()
        try:
            if HTTP_CLIENT == "curl_cffi":
                r = curl_requests.get(url, timeout=CURL_CFFI_TIMEOUT, impersonate=CURL_CFFI_IMPERSONATE, verify=REQUEST_VERIFY_SSL, allow_redirects=REQUEST_ALLOW_REDIRECTS, headers=DEFAULT_HEADERS)
                r.raise_for_status(); html = r.text
                return FetchResult(html, r.url, r.status_code, dict(r.headers), int((time.time()-started)*1000), "curl_cffi", detect_block_signals(html, dict(r.headers), r.status_code))
            s = requests.Session(); s.headers.update(DEFAULT_HEADERS)
            r = s.get(url, timeout=REQUEST_TIMEOUT, verify=REQUEST_VERIFY_SSL, allow_redirects=REQUEST_ALLOW_REDIRECTS)
            r.raise_for_status(); enc = r.apparent_encoding or r.encoding or "utf-8"; html = r.content.decode(enc, errors="replace")
            return FetchResult(html, str(r.url), r.status_code, dict(r.headers), int((time.time()-started)*1000), "requests", detect_block_signals(html, dict(r.headers), r.status_code))
        except Exception as exc:
            last_exc = exc
    raise RuntimeError(f"Static fetch failed for {url}: {last_exc}")
