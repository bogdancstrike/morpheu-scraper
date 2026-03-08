from __future__ import annotations

from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
from adaptive_scraper.utils.common import clean_text, safe_json_loads

def parse_jsonld_blocks(soup: BeautifulSoup) -> List[Any]:
    blocks = []
    for tag in soup.select('script[type="application/ld+json"]'):
        raw = tag.get_text(strip=True)
        if not raw:
            continue
        parsed = safe_json_loads(raw)
        if parsed is not None:
            blocks.append(parsed)
    return blocks

def flatten_jsonld_items(block: Any) -> List[dict]:
    items: List[dict] = []
    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if "@graph" in node and isinstance(node["@graph"], list):
                for item in node["@graph"]:
                    walk(item)
            else:
                items.append(node)
        elif isinstance(node, list):
            for item in node:
                walk(item)
    walk(block)
    return items

def extract_article_candidates_from_jsonld(soup: BeautifulSoup) -> List[dict]:
    results = []
    for block in parse_jsonld_blocks(soup):
        for item in flatten_jsonld_items(block):
            item_type = item.get("@type")
            types = item_type if isinstance(item_type, list) else [item_type]
            if any(t in ("NewsArticle", "Article", "BlogPosting", "LiveBlogPosting") for t in types if t):
                results.append(item)
    return results

def extract_author(item: dict) -> Optional[str]:
    author = item.get("author")
    if isinstance(author, str):
        return clean_text(author)
    if isinstance(author, dict):
        return clean_text(author.get("name"))
    if isinstance(author, list):
        names = []
        for a in author:
            if isinstance(a, str):
                v = clean_text(a)
            elif isinstance(a, dict):
                v = clean_text(a.get("name"))
            else:
                v = None
            if v:
                names.append(v)
        return ", ".join(names) if names else None
    return None

def extract_jsonld_article_data(soup: BeautifulSoup) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    candidates = extract_article_candidates_from_jsonld(soup)
    if not candidates:
        return result
    item = candidates[0]
    result["title"] = clean_text(item.get("headline") or item.get("name"))
    result["summary"] = clean_text(item.get("description"))
    result["author"] = extract_author(item)
    result["posted_date"] = clean_text(item.get("datePublished"))
    result["updated_date"] = clean_text(item.get("dateModified"))
    result["canonical_url"] = clean_text(item.get("url"))
    result["section"] = clean_text(item.get("articleSection"))
    result["article_type"] = clean_text(item.get("@type") if isinstance(item.get("@type"), str) else None)
    publisher = item.get("publisher")
    if isinstance(publisher, dict):
        result["publisher"] = {
            "name": clean_text(publisher.get("name")),
            "url": clean_text(publisher.get("url")),
            "logo": clean_text((publisher.get("logo") or {}).get("url") if isinstance(publisher.get("logo"), dict) else None),
        }
    image = item.get("image")
    if isinstance(image, list):
        result["images"] = [clean_text(str(x)) for x in image if clean_text(str(x))]
    elif isinstance(image, str):
        result["images"] = [clean_text(image)]
    elif isinstance(image, dict):
        image_url = clean_text(image.get("url"))
        if image_url:
            result["images"] = [image_url]
    keywords = item.get("keywords")
    if isinstance(keywords, str):
        result["keywords"] = [x.strip() for x in keywords.split(",") if x.strip()]
    elif isinstance(keywords, list):
        result["keywords"] = [str(x).strip() for x in keywords if str(x).strip()]
    return result
