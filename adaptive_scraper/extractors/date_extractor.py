from __future__ import annotations

from typing import Optional

from htmldate import find_date


def extract_date(url: str, html: str) -> Optional[str]:
    try:
        value = find_date(
            html,
            url=url,
            extensive_search=True,
            original_date=True,
        )
        return value or None
    except Exception:
        return None