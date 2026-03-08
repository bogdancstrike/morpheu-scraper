from __future__ import annotations

from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from adaptive_scraper.config import MAX_CARDS_FROM_PAGE, MIN_ARTICLE_WORDS, MIN_TITLE_LENGTH, USE_SELECTOLAX
from adaptive_scraper.utils.common import clean_text, domain_from_url, looks_like_article_url


def element_css_signature(node: Tag) -> Optional[str]:
    classes = [c for c in (node.get("class") or []) if isinstance(c, str)]
    node_id = node.get("id")
    if node_id:
        return f"{node.name}#{node_id}"
    if classes:
        return f"{node.name}." + ".".join(classes[:3])
    return node.name


def score_candidate_listing_container(node: Tag, base_url: str, domain: str) -> int:
    score = 0
    text = clean_text(node.get_text(" ", strip=True)) or ""
    identity = f"{node.name} {' '.join(node.get('class', []))} {node.get('id', '')}".lower()
    article_links = []
    for a in node.select("a[href]"):
        href = a.get("href")
        if href and looks_like_article_url(urljoin(base_url, href), domain):
            article_links.append(urljoin(base_url, href))
    if 2 <= len(set(article_links)) <= 100:
        score += len(set(article_links)) * 20
    score += len(node.select("h1, h2, h3, h4")) * 10
    if any(k in identity for k in ["feed", "list", "listing", "stories", "articles", "news", "grid", "stream"]):
        score += 40
    if any(k in identity for k in ["footer", "header", "nav", "menu", "sidebar", "cookie"]):
        score -= 80
    wc = len(text.split())
    if 30 <= wc <= 2500:
        score += 20
    return score


def mine_listing_selectors(html: str, base_url: str, domain: str) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    candidates = []
    for node in soup.find_all(["section", "div", "main", "article", "ul"]):
        score = score_candidate_listing_container(node, base_url, domain)
        if score > 0:
            sig = element_css_signature(node)
            if sig:
                candidates.append((sig, score))
    by_selector = {}
    for sig, score in candidates:
        by_selector[sig] = max(by_selector.get(sig, 0), score)
    return [sel for sel, _ in sorted(by_selector.items(), key=lambda x: x[1], reverse=True)[:12]]


def score_candidate_article_container(node: Tag, base_url: str) -> int:
    score = 0
    identity = f"{node.name} {' '.join(node.get('class', []))} {node.get('id', '')}".lower()
    text = clean_text(node.get_text("\n", strip=True)) or ""
    wc = len(text.split())
    if node.name == "article":
        score += 120
    if any(k in identity for k in ["article", "story", "content", "entry", "post", "body"]):
        score += 60
    if wc >= 150:
        score += min(wc, 2500) // 8
    if node.select_one("h1"):
        score += 60
    if node.find("time"):
        score += 20
    if node.find_all("p"):
        score += min(len(node.find_all("p")) * 5, 80)
    return score


def mine_article_container_selectors(html: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    candidates = []
    for node in soup.find_all(["article", "main", "section", "div"]):
        score = score_candidate_article_container(node, base_url)
        if score > 0:
            sig = element_css_signature(node)
            if sig:
                candidates.append((sig, score))
    by_selector = {}
    for sig, score in candidates:
        by_selector[sig] = max(by_selector.get(sig, 0), score)
    return [sel for sel, _ in sorted(by_selector.items(), key=lambda x: x[1], reverse=True)[:12]]


def extract_main_text_from_best_container(html: str, url: str, selectors: List[str]) -> Optional[str]:
    soup = BeautifulSoup(html, "lxml")
    for sel in selectors:
        try:
            nodes = soup.select(sel)
        except Exception:
            continue
        for node in nodes[:5]:
            text = clean_text(node.get_text("\n", strip=True))
            if text and len(text.split()) >= MIN_ARTICLE_WORDS:
                return text
    return None


def extract_article_cards_from_html(html: str, base_url: str, selectors: List[str]) -> List[dict]:
    soup = BeautifulSoup(html, "lxml")
    domain = domain_from_url(base_url)
    cards = []
    seen = set()
    default_selectors = selectors or ["article", "[class*='article']", "[class*='story']", "[class*='card']", "[class*='item']", "[class*='post']", "main", "section"]

    def extract_from_node(node):
        link = node.select_one("a[href]")
        if not link:
            return None
        href = link.get("href")
        if not href:
            return None
        full_url = urljoin(base_url, href)
        if not looks_like_article_url(full_url, domain):
            return None
        title = None
        for sel in ["h1", "h2", "h3", "h4", "[class*='title']", "[class*='headline']"]:
            t = node.select_one(sel)
            if t:
                title = clean_text(t.get_text(" ", strip=True))
                if title:
                    break
        if not title:
            title = clean_text(link.get_text(" ", strip=True))
        if not title or len(title) < MIN_TITLE_LENGTH:
            return None
        return {"url": full_url, "title": title, "subtitle": None, "author": None, "authors": None, "posted_date": None, "updated_date": None, "summary": None, "image": None, "section": None, "comments_count": None, "likes": None, "shares": None}

    for sel in default_selectors:
        try:
            nodes = soup.select(sel)
        except Exception:
            continue
        for node in nodes:
            card = extract_from_node(node)
            if card and card["url"] not in seen:
                seen.add(card["url"])
                cards.append(card)

    if USE_SELECTOLAX:
        try:
            from selectolax.parser import HTMLParser
            tree = HTMLParser(html)
            for node in tree.css("a"):
                href = node.attributes.get("href")
                if not href:
                    continue
                full = urljoin(base_url, href)
                if not looks_like_article_url(full, domain) or full in seen:
                    continue
                text = clean_text(node.text())
                if not text or len(text) < MIN_TITLE_LENGTH:
                    continue
                seen.add(full)
                cards.append({"url": full, "title": text, "subtitle": None, "author": None, "authors": None, "posted_date": None, "updated_date": None, "summary": None, "image": None, "section": None, "comments_count": None, "likes": None, "shares": None})
                if len(cards) >= MAX_CARDS_FROM_PAGE:
                    break
        except Exception:
            pass
    return cards
