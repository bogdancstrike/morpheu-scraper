from __future__ import annotations
from typing import Dict, List
BLOCK_MARKERS = {
    "cloudflare": ["cloudflare", "attention required", "checking your browser", "cf-browser-verification"],
    "akamai": ["akamai", "access denied", "reference #"],
    "datadome": ["datadome"],
    "captcha": ["captcha", "recaptcha", "hcaptcha", "verify you are human"],
    "js_challenge": ["enable javascript", "javascript is required"],
    "bot_protection": ["bot protection", "security check"],
}

def detect_block_signals(html: str, headers: Dict[str, str] | None = None, status_code: int | None = None) -> List[str]:
    signals: List[str] = []
    lowered = (html or "").lower()
    for signal, needles in BLOCK_MARKERS.items():
        if any(needle in lowered for needle in needles):
            signals.append(signal)
    headers = {str(k).lower(): str(v).lower() for k, v in (headers or {}).items()}
    server = headers.get("server", "")
    if "cloudflare" in server and "cloudflare" not in signals:
        signals.append("cloudflare")
    if status_code in {403, 429, 503}:
        signals.append(f"http_{status_code}")
    return signals

def likely_paywalled(html: str) -> bool:
    lowered = (html or "").lower()
    return any(token in lowered for token in ["subscribe to continue", "abonează-te", "subscriber-only", "premium content"])

def likely_liveblog(title: str | None, html: str | None) -> bool:
    content = f"{title or ''} {html or ''}".lower()
    return any(token in content for token in ["live", "live blog", "ultima oră", "breaking live"])
