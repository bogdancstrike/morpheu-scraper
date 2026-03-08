from __future__ import annotations
from typing import Any, Dict, List, Optional
import extruct
from adaptive_scraper.config import USE_EXTRUCT
from adaptive_scraper.utils.common import clean_text

def extract_with_extruct(html: str, url: str) -> Dict[str, Any]:
    if not USE_EXTRUCT:
        return {}
    try:
        data = extruct.extract(html, base_url=url, syntaxes=["json-ld", "microdata", "opengraph", "rdfa", "dublincore"], uniform=True)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def _pick_first_str(values: List[Any]) -> Optional[str]:
    for value in values:
        if isinstance(value, str):
            cleaned = clean_text(value)
            if cleaned:
                return cleaned
    return None

def _extract_author(item: dict) -> Optional[str]:
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

def normalize_extruct_metadata(extruct_data: Dict[str, Any]) -> Dict[str, Any]:
    result = {"title": None, "summary": None, "author": None, "posted_date": None, "updated_date": None, "canonical_url": None, "images": None, "keywords": None, "section": None, "tags": None, "categories": None}
    if not extruct_data:
        return result
    jsonld = extruct_data.get("json-ld") or []
    for item in jsonld:
        if not isinstance(item, dict):
            continue
        item_type = item.get("@type")
        types = item_type if isinstance(item_type, list) else [item_type]
        if any(t in ("NewsArticle", "Article", "BlogPosting") for t in types if t):
            result["title"] = result["title"] or clean_text(item.get("headline") or item.get("name"))
            result["summary"] = result["summary"] or clean_text(item.get("description"))
            result["author"] = result["author"] or _extract_author(item)
            result["posted_date"] = result["posted_date"] or clean_text(item.get("datePublished"))
            result["updated_date"] = result["updated_date"] or clean_text(item.get("dateModified"))
            result["canonical_url"] = result["canonical_url"] or clean_text(item.get("url"))
            result["section"] = result["section"] or clean_text(item.get("articleSection"))
            raw_img = item.get("image")
            if not result["images"]:
                if isinstance(raw_img, list):
                    imgs = [clean_text(str(x)) for x in raw_img if clean_text(str(x))]
                    if imgs: result["images"] = imgs
                elif isinstance(raw_img, str):
                    img = clean_text(raw_img)
                    if img: result["images"] = [img]
            raw_keywords = item.get("keywords")
            if not result["keywords"]:
                if isinstance(raw_keywords, str):
                    result["keywords"] = [x.strip() for x in raw_keywords.split(",") if x.strip()]
                elif isinstance(raw_keywords, list):
                    result["keywords"] = [str(x).strip() for x in raw_keywords if str(x).strip()]
    opengraph = extruct_data.get("opengraph") or []
    if opengraph and isinstance(opengraph, list):
        first_og = opengraph[0]
        if isinstance(first_og, dict):
            props = first_og.get("properties") or {}
            result["title"] = result["title"] or clean_text(props.get("og:title"))
            result["summary"] = result["summary"] or clean_text(props.get("og:description"))
            result["canonical_url"] = result["canonical_url"] or clean_text(props.get("og:url"))
            if not result["images"] and props.get("og:image"):
                img = clean_text(props.get("og:image"))
                if img: result["images"] = [img]
    microdata = extruct_data.get("microdata") or []
    for item in microdata:
        if not isinstance(item, dict):
            continue
        props = item.get("properties") or {}
        result["title"] = result["title"] or clean_text(props.get("headline") or props.get("name"))
        result["summary"] = result["summary"] or clean_text(props.get("description"))
        if not result["posted_date"]:
            pd = props.get("datePublished")
            result["posted_date"] = _pick_first_str(pd) if isinstance(pd, list) else clean_text(pd)
    return result
