from __future__ import annotations
from adaptive_scraper.extractors.dom import extract_article_cards_from_html
from adaptive_scraper.utils.common import looks_like_article_url, clean_text

def dedupe_cards(cards: list[dict]) -> list[dict]:
    merged = {}
    for card in cards:
        url = card.get("url")
        if not url:
            continue
        if url not in merged:
            merged[url] = dict(card)
            continue
        for key, value in card.items():
            if merged[url].get(key) in (None, "", [], {}) and value not in (None, "", [], {}):
                merged[url][key] = value
    return list(merged.values())

def collect_listing_cards(url: str, domain: str, cfg, browser_fetch_page_fn, fetch_static_fn, writer=None) -> tuple[list[dict], str]:
    cards = []
    used_method = cfg.method
    if cfg.method in ("api_intercept", "playwright_render") or cfg.use_browser:
        browser_data = browser_fetch_page_fn(url, cfg, domain, writer=writer)
        if cfg.use_api_intercept and browser_data.api_cards:
            cards.extend(browser_data.api_cards)
        cards.extend(extract_article_cards_from_html(browser_data.rendered_html, url, cfg.listing_selectors))
        for a in browser_data.anchors:
            full = a["url"]
            if looks_like_article_url(full, domain):
                txt = clean_text(a.get("text"))
                if txt:
                    cards.append({"url": full, "title": txt, "subtitle": None, "author": None, "authors": None, "posted_date": None, "updated_date": None, "summary": None, "image": None, "section": None, "comments_count": None, "likes": None, "shares": None})
        used_method = "api_intercept" if cfg.use_api_intercept and browser_data.api_cards else "playwright_render"
    else:
        html = fetch_static_fn(url).html
        if writer:
            writer.write_debug_html(f"listing_static_{domain}", html)
        cards.extend(extract_article_cards_from_html(html, url, cfg.listing_selectors))
        used_method = "static_trafilatura"
    cards = [c for c in dedupe_cards(cards) if c.get("url") and c.get("title")]
    return cards[:cfg.max_articles], used_method
