from __future__ import annotations

from typing import Any, Dict

from bs4 import BeautifulSoup
from readability import Document


def extract_readability(html: str) -> Dict[str, Any]:
    try:
        doc = Document(html)
        summary_html = doc.summary()
        title = doc.title()

        soup = BeautifulSoup(summary_html, "lxml")
        text = soup.get_text("\n", strip=True)

        return {
            "title": title,
            "content": text,
            "summary_html": summary_html,
        }
    except Exception:
        return {
            "title": None,
            "content": None,
            "summary_html": None,
        }