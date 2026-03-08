from __future__ import annotations
import json
from dataclasses import asdict
from typing import Any, Dict
from adaptive_scraper.config import CONFIG_FILE, SiteConfig

def load_all_site_configs() -> Dict[str, Dict[str, Any]]:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def load_site_config(domain: str) -> SiteConfig:
    raw = load_all_site_configs().get(domain)
    if not raw:
        return SiteConfig()
    try:
        return SiteConfig(**raw)
    except Exception:
        return SiteConfig()

def save_site_config(domain: str, cfg: SiteConfig) -> None:
    all_cfg = load_all_site_configs()
    all_cfg[domain] = asdict(cfg)
    CONFIG_FILE.write_text(json.dumps(all_cfg, ensure_ascii=False, indent=2), encoding="utf-8")
