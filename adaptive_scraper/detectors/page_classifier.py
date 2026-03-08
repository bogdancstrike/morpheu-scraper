from __future__ import annotations
from bs4 import BeautifulSoup
from adaptive_scraper.config import MAX_ANCHORS_TO_SCAN
from adaptive_scraper.extractors.jsonld import extract_article_candidates_from_jsonld
from adaptive_scraper.utils.common import clean_text, count_words, domain_from_url, is_same_domain, looks_like_article_url, path_from_url

def classify_page(url: str, html: str, trafilatura_data: dict | None) -> tuple[str, dict]:
    soup = BeautifulSoup(html, "lxml")
    path = path_from_url(url).strip("/")
    article_score = 0.0
    listing_score = 0.0
    jsonld_articles = extract_article_candidates_from_jsonld(soup)
    if jsonld_articles:
        article_score += 0.5 if len(jsonld_articles) == 1 else 0.25
    text = clean_text((trafilatura_data or {}).get("text"))
    title = clean_text((trafilatura_data or {}).get("title"))
    author = clean_text((trafilatura_data or {}).get("author"))
    date = clean_text((trafilatura_data or {}).get("date"))
    if title: article_score += 0.1
    if text and (count_words(text) or 0) >= 250: article_score += 0.25
    if author or date: article_score += 0.1
    links = soup.select("a[href]")
    domain = domain_from_url(url)
    same_domain_links = 0
    articleish_links = 0
    from urllib.parse import urljoin
    for a in links[:MAX_ANCHORS_TO_SCAN]:
        href = a.get("href")
        if not href: continue
        full = urljoin(url, href)
        if is_same_domain(full, domain):
            same_domain_links += 1
            if looks_like_article_url(full, domain): articleish_links += 1
    if articleish_links >= 8: listing_score += 0.4
    if same_domain_links >= 25: listing_score += 0.25
    if not path: listing_score += 0.2
    return ("article" if article_score >= listing_score else "listing", {"article": round(article_score, 3), "listing": round(listing_score, 3)})
