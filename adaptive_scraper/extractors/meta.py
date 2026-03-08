from __future__ import annotations
from typing import Any, Dict, Optional
from bs4 import BeautifulSoup
from adaptive_scraper.utils.common import clean_text

def extract_meta_content(soup: BeautifulSoup, attr_name: str, attr_value: str) -> Optional[str]:
    tag = soup.find("meta", attrs={attr_name: attr_value})
    return clean_text(tag.get("content")) if tag else None

def extract_open_graph_data(soup: BeautifulSoup) -> Dict[str, Any]:
    return {
        "og_title": extract_meta_content(soup, "property", "og:title"),
        "og_description": extract_meta_content(soup, "property", "og:description"),
        "og_image": extract_meta_content(soup, "property", "og:image"),
        "og_url": extract_meta_content(soup, "property", "og:url"),
        "article_published_time": extract_meta_content(soup, "property", "article:published_time"),
        "article_modified_time": extract_meta_content(soup, "property", "article:modified_time"),
        "article_author": extract_meta_content(soup, "property", "article:author"),
        "author": extract_meta_content(soup, "name", "author"),
        "keywords": extract_meta_content(soup, "name", "keywords"),
        "description": extract_meta_content(soup, "name", "description"),
    }

def extract_canonical_url(soup: BeautifulSoup, url: str) -> Optional[str]:
    link = soup.find("link", rel="canonical")
    if link and link.get("href"):
        return clean_text(link.get("href"))
    return url
