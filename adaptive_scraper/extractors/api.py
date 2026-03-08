from __future__ import annotations

import re
from typing import Any, List, Optional, Tuple

from adaptive_scraper.utils.common import clean_text, safe_int, safe_json_loads, is_same_domain, looks_like_article_url


def find_text_candidates_in_json(obj: Any, path: str = "") -> List[Tuple[str, str]]:
    results = []
    interesting_keys = {"text", "body", "content", "article", "description", "summary", "lead", "headline", "title", "caption", "rendered", "story", "articlebody", "excerpt"}
    if isinstance(obj, dict):
        for k, v in obj.items():
            current_path = f"{path}.{k}" if path else k
            if isinstance(v, str):
                cleaned = clean_text(v)
                if cleaned and (len(cleaned) > 150 or k.lower() in interesting_keys):
                    results.append((current_path, cleaned))
            else:
                results.extend(find_text_candidates_in_json(v, current_path))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            results.extend(find_text_candidates_in_json(item, f"{path}[{i}]"))
    return results


def score_article_text(text: Optional[str]) -> int:
    if not text:
        return 0
    words = text.split()
    score = len(words)
    if len(words) >= 40:
        score += 50
    if "\n\n" in text:
        score += 100
    if re.search(r"\b(publicat|autor|update|românia|romania|video|analiză|interviu|breaking)\b", text.lower()):
        score += 50
    return score


def extract_best_api_text(payload_text: str) -> Tuple[Optional[str], int]:
    payload_text = payload_text.strip()
    parsed = safe_json_loads(payload_text)
    if parsed is None:
        txt = clean_text(payload_text)
        return txt, score_article_text(txt)
    best_text, best_score = None, 0
    for _, candidate in find_text_candidates_in_json(parsed):
        score = score_article_text(candidate)
        if score > best_score:
            best_text, best_score = candidate, score
    return best_text, best_score


def extract_cards_from_api_payload(payload_text: str, base_url: str, domain: str) -> List[dict]:
    from urllib.parse import urljoin
    parsed = safe_json_loads(payload_text)
    if parsed is None:
        return []
    cards, seen = [], set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            url_value = None
            for url_key in ["url", "link", "canonical_url", "href", "permalink"]:
                if isinstance(node.get(url_key), str):
                    url_value = urljoin(base_url, node[url_key])
                    break
            title = None
            for title_key in ["title", "headline", "name"]:
                if isinstance(node.get(title_key), str):
                    title = clean_text(node[title_key])
                    if title:
                        break
            summary = None
            for sum_key in ["summary", "description", "excerpt", "lead"]:
                if isinstance(node.get(sum_key), str):
                    summary = clean_text(node[sum_key])
                    if summary:
                        break
            if url_value and title and is_same_domain(url_value, domain) and looks_like_article_url(url_value, domain) and url_value not in seen:
                seen.add(url_value)
                author = node.get("author")
                if isinstance(author, dict):
                    author = clean_text(author.get("name"))
                elif isinstance(author, str):
                    author = clean_text(author)
                else:
                    author = None
                image = None
                for img_key in ["image", "thumbnail", "image_url"]:
                    raw_img = node.get(img_key)
                    if isinstance(raw_img, str):
                        image = clean_text(raw_img)
                        break
                    if isinstance(raw_img, dict):
                        image = clean_text(raw_img.get("url"))
                        break
                cards.append({
                    "url": url_value,
                    "title": title,
                    "subtitle": None,
                    "author": author,
                    "authors": [author] if author else None,
                    "posted_date": clean_text(node.get("datePublished") or node.get("published_at") or node.get("date")),
                    "updated_date": clean_text(node.get("dateModified") or node.get("updated_at")),
                    "summary": summary,
                    "image": image,
                    "section": clean_text(node.get("section") or node.get("category")),
                    "comments_count": safe_int(node.get("comments_count")),
                    "likes": safe_int(node.get("likes")),
                    "shares": safe_int(node.get("shares")),
                })
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(parsed)
    return cards
