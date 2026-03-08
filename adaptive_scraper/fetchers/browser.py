from __future__ import annotations
import time
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright
from adaptive_scraper.config import ANTI_BOT_JITTER_MAX_MS, ANTI_BOT_JITTER_MIN_MS, BLOCK_NON_ESSENTIAL_RESOURCES, BROWSER_PERSIST_STORAGE, HEADLESS, MAX_API_PATTERNS, PLAYWRIGHT_NETWORK_IDLE_TIMEOUT_MS, PLAYWRIGHT_PAGE_WAIT_AFTER_LOAD_MS, PLAYWRIGHT_STORAGE_STATE_PATH, PLAYWRIGHT_TIMEOUT_MS, SCROLL_STABLE_ROUNDS_TO_STOP, USER_AGENT
from adaptive_scraper.detectors.anti_bot import detect_block_signals
from adaptive_scraper.extractors.api import extract_best_api_text, extract_cards_from_api_payload
from adaptive_scraper.extractors.hydration import extract_hydration_data
from adaptive_scraper.models import BrowserPageData
from adaptive_scraper.utils.common import add_jitter, clean_text, dedupe_preserve_order

def _install_resource_blocking(context) -> None:
    def handle_route(route):
        req = route.request
        url = req.url.lower()
        blocked = req.resource_type in {"image", "media", "font"} or any(x in url for x in ["doubleclick", "googletagmanager", "google-analytics", "facebook.net", "hotjar", "scorecardresearch"])
        if blocked: route.abort()
        else: route.continue_()
    context.route("**/*", handle_route)

def browser_fetch_page(url: str, site_cfg, domain: str, writer=None) -> BrowserPageData:
    intercepted_payloads = []
    started = time.time()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context_args = {"user_agent": USER_AGENT, "locale": "ro-RO", "ignore_https_errors": True}
        if BROWSER_PERSIST_STORAGE:
            context_args["storage_state"] = PLAYWRIGHT_STORAGE_STATE_PATH
        context = browser.new_context(**context_args)
        if BLOCK_NON_ESSENTIAL_RESOURCES:
            _install_resource_blocking(context)
        page = context.new_page()
        main_response = {"status": None}
        def on_response(resp):
            try:
                ct = (resp.headers.get("content-type") or "").lower()
                if page.url == resp.url and main_response["status"] is None:
                    main_response["status"] = resp.status
                if not any(x in ct for x in ["json", "javascript", "html", "ld+json"]):
                    return
                body = resp.text()
                if body and len(body) >= 80:
                    intercepted_payloads.append({"url": resp.url, "content_type": ct, "body": body})
            except Exception:
                pass
        page.on("response", on_response)
        add_jitter(ANTI_BOT_JITTER_MIN_MS, ANTI_BOT_JITTER_MAX_MS)
        page.goto(url, wait_until="domcontentloaded", timeout=PLAYWRIGHT_TIMEOUT_MS)
        try: page.wait_for_load_state("networkidle", timeout=PLAYWRIGHT_NETWORK_IDLE_TIMEOUT_MS)
        except PlaywrightTimeoutError: pass
        page.wait_for_timeout(PLAYWRIGHT_PAGE_WAIT_AFTER_LOAD_MS)
        if site_cfg.use_infinite_scroll:
            previous_height = 0; stable_rounds = 0
            for _ in range(site_cfg.scroll_rounds):
                current_height = page.evaluate("document.body.scrollHeight")
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(site_cfg.scroll_wait_ms)
                new_height = page.evaluate("document.body.scrollHeight")
                if new_height <= current_height and new_height == previous_height: stable_rounds += 1
                else: stable_rounds = 0
                previous_height = new_height
                if stable_rounds >= SCROLL_STABLE_ROUNDS_TO_STOP: break
        rendered_html = page.content(); final_url = page.url; title = clean_text(page.title())
        anchors, seen = [], set()
        for a in page.locator("a[href]").all():
            try:
                href = a.get_attribute("href"); text = a.text_content()
                if not href: continue
                full = urljoin(final_url, href)
                if full in seen: continue
                seen.add(full); anchors.append({"url": full, "text": clean_text(text)})
            except Exception: continue
        if BROWSER_PERSIST_STORAGE: context.storage_state(path=PLAYWRIGHT_STORAGE_STATE_PATH)
        browser.close()
    if writer: writer.write_debug_html(f"rendered_{domain}", rendered_html)
    api_cards, best_api_text, best_api_text_score, api_patterns = [], None, 0, []
    for idx, payload in enumerate(intercepted_payloads, start=1):
        if writer: writer.write_debug_api_payload(idx, payload["url"], payload["body"])
        txt, score = extract_best_api_text(payload["body"])
        if score > best_api_text_score: best_api_text, best_api_text_score = txt, score
        cards = extract_cards_from_api_payload(payload["body"], final_url, domain)
        if cards:
            api_cards.extend(cards); api_patterns.append(payload["url"])
    soup = BeautifulSoup(rendered_html, "lxml")
    hydration_data, hydration_keys = extract_hydration_data(soup)
    import json
    for hyd in hydration_data:
        try: api_cards.extend(extract_cards_from_api_payload(json.dumps(hyd, ensure_ascii=False), final_url, domain))
        except Exception: pass
    return BrowserPageData(rendered_html=rendered_html, final_url=final_url, status_code=main_response["status"], latency_ms=int((time.time() - started) * 1000), title=title, anchors=anchors, api_cards=api_cards, best_api_text=best_api_text, best_api_text_score=best_api_text_score, api_patterns=dedupe_preserve_order(api_patterns)[:MAX_API_PATTERNS], hydration_data=hydration_data, hydration_keys=dedupe_preserve_order(hydration_keys), block_signals=detect_block_signals(rendered_html, {}, main_response["status"]))
