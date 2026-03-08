from __future__ import annotations

import argparse
from dataclasses import asdict
from typing import Any

from bs4 import BeautifulSoup

from adaptive_scraper.cache import get_cache_key, is_cached_url, load_scraped_cache, mark_cached
from adaptive_scraper.config import MIN_ARTICLE_WORDS, OUTPUT_DIR, SiteConfig
from adaptive_scraper.crawler.listing import collect_listing_cards
from adaptive_scraper.detectors.page_classifier import classify_page
from adaptive_scraper.extractors.date_extractor import extract_date
from adaptive_scraper.extractors.dom import extract_main_text_from_best_container, mine_article_container_selectors, mine_listing_selectors
from adaptive_scraper.extractors.extruct_extractor import extract_with_extruct, normalize_extruct_metadata
from adaptive_scraper.extractors.hydration import extract_hydration_data
from adaptive_scraper.extractors.jsonld import extract_jsonld_article_data
from adaptive_scraper.extractors.meta import extract_canonical_url, extract_open_graph_data
from adaptive_scraper.extractors.readability_extractor import extract_readability
from adaptive_scraper.extractors.trafilatura_extractor import extract_trafilatura_json
from adaptive_scraper.fetchers.browser import browser_fetch_page
from adaptive_scraper.fetchers.static import fetch_static
from adaptive_scraper.models import Article, ArticleRecord, Engagement, Metadata, Publisher
from adaptive_scraper.scoring.merge import pick_field
from adaptive_scraper.scoring.quality import article_has_enough_content, score_record
from adaptive_scraper.site_store import load_site_config, save_site_config
from adaptive_scraper.utils.common import clean_text, count_words, dedupe_preserve_order, domain_from_url, estimate_reading_time_minutes, maybe_list, normalize_url, now_epoch, path_from_url
from adaptive_scraper.writer import RunWriter


def discover_site_strategy(url: str, domain: str, cfg: SiteConfig, writer: RunWriter | None = None) -> SiteConfig:
    discovered = SiteConfig(**asdict(cfg))
    discovered.discovered_at = now_epoch()
    static_result = fetch_static(url)
    static_html = static_result.html
    if writer:
        writer.write_debug_html(f"static_{domain}", static_html)
    static_data = extract_trafilatura_json(static_html, url)
    discovered.listing_selectors = mine_listing_selectors(static_html, url, domain)
    discovered.article_container_selectors = mine_article_container_selectors(static_html, url)
    page_type, confidence = classify_page(url, static_html, static_data)
    discovered.page_type = page_type
    discovered.notes = f"Detected via classifier: {confidence}"
    best_method = "static_trafilatura"
    use_browser = False
    use_api = False
    if page_type == "listing" or not clean_text(static_data.get("text")):
        browser_data = browser_fetch_page(url, discovered, domain, writer=writer)
        use_browser = True
        best_method = "playwright_render"
        if browser_data.api_cards:
            use_api = True
            best_method = "api_intercept"
            discovered.api_patterns = browser_data.api_patterns
        discovered.hydration_keys = browser_data.hydration_keys
        discovered.waf_signals = browser_data.block_signals
        if page_type == "listing" and browser_data.rendered_html:
            discovered.listing_selectors = dedupe_preserve_order(mine_listing_selectors(browser_data.rendered_html, url, domain) + discovered.listing_selectors)[:15]
            if len(browser_data.api_cards) >= 5:
                discovered.use_infinite_scroll = True
    discovered.method = best_method
    discovered.use_browser = use_browser
    discovered.use_api_intercept = use_api
    discovered.last_success_at = now_epoch()
    return discovered


def build_article_record_from_sources(url: str, website: str, html: str, extracted: dict[str, Any], site_cfg: SiteConfig, fallback_card: dict | None = None, fetch_method: str = "static") -> ArticleRecord:
    soup = BeautifulSoup(html, "lxml")
    og = extract_open_graph_data(soup)
    jsonld = extract_jsonld_article_data(soup)
    extruct_data = normalize_extruct_metadata(extract_with_extruct(html, url))
    readability = extract_readability(html)
    htmld = extract_date(url, html)
    hydration_data, _ = extract_hydration_data(soup)
    text = clean_text(extracted.get("text"))
    dom_used = False
    if not text or (count_words(text) or 0) < MIN_ARTICLE_WORDS:
        selectors = site_cfg.article_container_selectors or mine_article_container_selectors(html, url)
        better_text = extract_main_text_from_best_container(html, url, selectors)
        if better_text and len(better_text.split()) > len((text or '').split()):
            text = better_text
            dom_used = True
    title, title_source, title_conf = pick_field("title", [("jsonld", jsonld.get("title")), ("trafilatura", clean_text(extracted.get("title"))), ("extruct", extruct_data.get("title")), ("og", clean_text(og.get("og_title"))), ("fallback_card", clean_text((fallback_card or {}).get("title"))), ("readability", readability.get("title"))])
    author, author_source, author_conf = pick_field("author", [("jsonld", jsonld.get("author")), ("trafilatura", clean_text(extracted.get("author"))), ("extruct", extruct_data.get("author")), ("og", clean_text(og.get("author") or og.get("article_author"))), ("fallback_card", clean_text((fallback_card or {}).get("author")))])
    posted_date, date_source, date_conf = pick_field("posted_date", [("jsonld", jsonld.get("posted_date")), ("htmldate", htmld), ("trafilatura", clean_text(extracted.get("date"))), ("extruct", extruct_data.get("posted_date")), ("og", clean_text(og.get("article_published_time"))), ("fallback_card", clean_text((fallback_card or {}).get("posted_date")))])
    updated_date, updated_source, updated_conf = pick_field("updated_date", [("jsonld", jsonld.get("updated_date")), ("extruct", extruct_data.get("updated_date")), ("og", clean_text(og.get("article_modified_time"))), ("fallback_card", clean_text((fallback_card or {}).get("updated_date")))])
    summary, summary_source, summary_conf = pick_field("summary", [("jsonld", jsonld.get("summary")), ("trafilatura", clean_text(extracted.get("description"))), ("extruct", extruct_data.get("summary")), ("og", clean_text(og.get("og_description") or og.get("description"))), ("fallback_card", clean_text((fallback_card or {}).get("summary")))])
    canonical, canonical_source, canonical_conf = pick_field("canonical_url", [("jsonld", jsonld.get("canonical_url")), ("extruct", extruct_data.get("canonical_url")), ("canonical", extract_canonical_url(soup, url)), ("og", clean_text(og.get("og_url")))])
    images = maybe_list(extracted.get("image")) or extruct_data.get("images") or maybe_list(jsonld.get("images")) or ([og.get("og_image")] if og.get("og_image") else None)
    publisher_data = jsonld.get("publisher") or {}
    article = Article(
        url=url,
        title=title,
        author=author,
        authors=[author] if author else None,
        posted_date=posted_date,
        updated_date=updated_date,
        content=text,
        summary=summary,
        language=clean_text(extracted.get("language")),
        word_count=count_words(text),
        reading_time_minutes=estimate_reading_time_minutes(text),
        section=clean_text((fallback_card or {}).get("section")) or extruct_data.get("section") or jsonld.get("section"),
        source=website,
        article_type=jsonld.get("article_type"),
    )
    engagement = Engagement(
        likes=(fallback_card or {}).get("likes"),
        shares=(fallback_card or {}).get("shares"),
        comments_count=(fallback_card or {}).get("comments_count"),
        views=None,
    )
    metadata = Metadata(
        tags=maybe_list(extracted.get("tags")),
        categories=maybe_list(extracted.get("categories")),
        images=images,
        videos=None,
        canonical_url=canonical,
        keywords=extruct_data.get("keywords") or maybe_list(og.get("keywords")),
        top_image=images[0] if images else None,
        publisher=Publisher(name=publisher_data.get("name"), url=publisher_data.get("url"), logo=publisher_data.get("logo")),
    )
    record = ArticleRecord(article=article, engagement=engagement, comments=[], metadata=metadata)
    record.trace.fetch_method = fetch_method
    record.trace.hydration_used = bool(hydration_data)
    record.trace.field_sources.update({
        "title": title_source or "",
        "author": author_source or "",
        "posted_date": date_source or "",
        "updated_date": updated_source or "",
        "summary": summary_source or "",
        "canonical_url": canonical_source or "",
        "content": "dom" if dom_used else "trafilatura",
    })
    record.trace.field_confidence.update({
        "title": title_conf,
        "author": author_conf,
        "posted_date": date_conf,
        "updated_date": updated_conf,
        "summary": summary_conf,
        "canonical_url": canonical_conf,
        "content": 0.85 if dom_used else 0.95,
    })
    return score_record(record, html)


def scrape_article_static(url: str, website: str, site_cfg: SiteConfig, fallback_card: dict | None = None) -> ArticleRecord | None:
    try:
        fetched = fetch_static(url)
        extracted = extract_trafilatura_json(fetched.html, url)
        record = build_article_record_from_sources(url, website, fetched.html, extracted, site_cfg, fallback_card=fallback_card, fetch_method=fetched.method)
        record.trace.static_fetch_succeeded = True
        record.trace.block_signals.extend(fetched.block_signals)
        record.crawl.response_status = fetched.status_code
        record.crawl.final_url = fetched.final_url
        record.crawl.fetch_latency_ms = fetched.latency_ms
        record.crawl.fetched_at_epoch = now_epoch()
        return record
    except Exception:
        return None


def scrape_article_browser(url: str, website: str, site_cfg: SiteConfig, fallback_card: dict | None = None, writer: RunWriter | None = None) -> ArticleRecord | None:
    try:
        cfg = SiteConfig(use_infinite_scroll=False, scroll_rounds=0)
        cfg.article_container_selectors = list(site_cfg.article_container_selectors)
        page = browser_fetch_page(url, cfg, website, writer=writer)
        extracted = extract_trafilatura_json(page.rendered_html, url)
        record = build_article_record_from_sources(url, website, page.rendered_html, extracted, site_cfg, fallback_card=fallback_card, fetch_method="playwright")
        record.trace.browser_fetch_succeeded = True
        record.trace.api_intercept_used = bool(page.api_cards)
        record.trace.hydration_used = bool(page.hydration_data)
        record.trace.block_signals.extend(page.block_signals)
        record.crawl.response_status = page.status_code
        record.crawl.final_url = page.final_url
        record.crawl.fetch_latency_ms = page.latency_ms
        record.crawl.fetched_at_epoch = now_epoch()
        return record
    except Exception:
        return None


def scrape_listing_site(url: str, domain: str, cfg: SiteConfig, writer: RunWriter, cache: dict) -> None:
    cards, listing_method = collect_listing_cards(url, domain, cfg, browser_fetch_page, fetch_static, writer=writer)
    article_index = 0
    print(f"Website: {domain} | URL: {url} | type=listing | method={listing_method} | cards={len(cards)}")
    for idx, card in enumerate(cards, start=1):
        article_url = card["url"]
        if is_cached_url(domain, article_url, cache):
            print(f"[{idx}/{len(cards)}] skipping cached {article_url}")
            writer.write_skipped_cached(article_url)
            continue
        print(f"[{idx}/{len(cards)}] scraping {article_url}")
        if cfg.method == "static_trafilatura" and not cfg.use_browser:
            record = scrape_article_static(article_url, domain, cfg, fallback_card=card)
            if not record or not article_has_enough_content(record, MIN_ARTICLE_WORDS):
                record = scrape_article_browser(article_url, domain, cfg, fallback_card=card, writer=writer)
        else:
            record = scrape_article_browser(article_url, domain, cfg, fallback_card=card, writer=writer)
            if not record or not article_has_enough_content(record, MIN_ARTICLE_WORDS):
                record = scrape_article_static(article_url, domain, cfg, fallback_card=card)
        if not record:
            writer.write_rejected(article_url, "could_not_extract_usable_article")
            continue
        canonical_key = get_cache_key(record)
        if canonical_key and is_cached_url(domain, canonical_key, cache):
            writer.write_skipped_cached(canonical_key, reason="canonical_already_cached")
            continue
        if not article_has_enough_content(record, MIN_ARTICLE_WORDS):
            writer.write_rejected(article_url, "low_quality", payload={"score": record.quality.overall_score, "words": record.article.word_count})
            continue
        article_index += 1
        saved_path = writer.write_article(article_index, record)
        mark_cached(domain, record, cache, output_file=str(saved_path))
    print(f"Finished. Saved {article_index} new article files.")


def scrape_single_article_site(url: str, domain: str, cfg: SiteConfig, writer: RunWriter, cache: dict) -> None:
    if is_cached_url(domain, url, cache):
        writer.write_skipped_cached(url)
        return
    record = scrape_article_browser(url, domain, cfg, writer=writer) if cfg.use_browser else scrape_article_static(url, domain, cfg)
    if (not record or not article_has_enough_content(record, MIN_ARTICLE_WORDS)) and cfg.use_browser:
        record = scrape_article_static(url, domain, cfg)
    elif not record or not article_has_enough_content(record, MIN_ARTICLE_WORDS):
        record = scrape_article_browser(url, domain, cfg, writer=writer)
    if not record:
        raise RuntimeError(f"Could not scrape article {url}")
    saved_path = writer.write_article(1, record)
    mark_cached(domain, record, cache, output_file=str(saved_path))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Adaptive scraper with smarter selector mining, anti-bot heuristics, hydration/API parsing, and richer extraction.")
    p.add_argument("--website", required=True, help="Domain or full URL, e.g. adevarul.ro")
    p.add_argument("--max-articles", type=int, default=None)
    p.add_argument("--scroll-rounds", type=int, default=None)
    p.add_argument("--scroll-wait-ms", type=int, default=None)
    p.add_argument("--no-follow-articles", action="store_true")
    p.add_argument("--force-rediscover", action="store_true")
    p.add_argument("--force-method", choices=["auto", "static_trafilatura", "playwright_render", "api_intercept"], default=None)
    p.add_argument("--force-page-type", choices=["auto", "listing", "article"], default=None)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    url = normalize_url(args.website)
    domain = domain_from_url(url)
    run_ts = now_epoch()
    writer = RunWriter(domain, run_ts, OUTPUT_DIR)
    cache = load_scraped_cache()
    cfg = SiteConfig() if args.force_rediscover else load_site_config(domain)
    if args.max_articles is not None:
        cfg.max_articles = args.max_articles
    if args.scroll_rounds is not None:
        cfg.scroll_rounds = args.scroll_rounds
    if args.scroll_wait_ms is not None:
        cfg.scroll_wait_ms = args.scroll_wait_ms
    if args.no_follow_articles:
        cfg.follow_article_links = False
    if args.force_method is not None:
        cfg.method = args.force_method
        cfg.use_browser = args.force_method in ("playwright_render", "api_intercept")
        cfg.use_api_intercept = args.force_method == "api_intercept"
    if args.force_page_type is not None:
        cfg.page_type = args.force_page_type
    if args.force_rediscover or cfg.method == "auto" or cfg.page_type == "auto":
        cfg = discover_site_strategy(url, domain, cfg, writer=writer)
        save_site_config(domain, cfg)
    cfg.last_success_at = now_epoch()
    save_site_config(domain, cfg)
    writer.write_site_config_snapshot(cfg)
    page_type = cfg.page_type if cfg.page_type != "auto" else ("listing" if path_from_url(url) in ("", "/") else "article")
    if page_type == "listing":
        scrape_listing_site(url, domain, cfg, writer, cache)
    else:
        scrape_single_article_site(url, domain, cfg, writer, cache)
    cfg.last_success_at = now_epoch()
    save_site_config(domain, cfg)
    writer.write_site_config_snapshot(cfg)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
