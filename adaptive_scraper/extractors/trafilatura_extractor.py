from __future__ import annotations

import json
from typing import Any, Dict

import trafilatura


def extract_trafilatura_json(html: str, url: str) -> Dict[str, Any]:
    try:
        raw = trafilatura.extract(
            html,
            url=url,
            output_format="json",
            include_comments=True,
            include_tables=False,
            include_images=True,
            include_links=False,
            favor_precision=True,
        )
        if not raw:
            return {}
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}