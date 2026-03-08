from __future__ import annotations
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any
from adaptive_scraper.config import MAX_DEBUG_API_PAYLOADS, SAVE_DEBUG_API_PAYLOADS, SAVE_DEBUG_HTML
from adaptive_scraper.models import ArticleRecord
from adaptive_scraper.utils.common import now_epoch, slugify

class RunWriter:
    def __init__(self, website: str, run_ts: int, base_output_dir: Path):
        self.website = website
        self.run_ts = run_ts
        self.run_dir = base_output_dir / f"{website}_{run_ts}"
        self.articles_dir = self.run_dir / "articles"
        self.debug_dir = self.run_dir / "debug"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.articles_dir.mkdir(parents=True, exist_ok=True)
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        self.index_payload = {"website": website, "run_started_at": run_ts, "updated_at": run_ts, "article_count": 0, "skipped_cached_count": 0, "rejected_count": 0, "articles": [], "skipped_cached": [], "rejected": []}
        self._write_index()
    def _write_index(self) -> None:
        self.index_payload["updated_at"] = now_epoch()
        (self.run_dir / "index.json").write_text(json.dumps(self.index_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    def write_site_config_snapshot(self, cfg: Any) -> None:
        (self.run_dir / "site_config_snapshot.json").write_text(json.dumps(asdict(cfg), ensure_ascii=False, indent=2), encoding="utf-8")
    def write_debug_html(self, name: str, html: str) -> None:
        if SAVE_DEBUG_HTML:
            (self.debug_dir / f"{slugify(name)}.html").write_text(html, encoding="utf-8")
    def write_debug_json(self, name: str, payload: Any) -> None:
        (self.debug_dir / f"{slugify(name)}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    def write_debug_api_payload(self, idx: int, source_url: str, body: str) -> None:
        if SAVE_DEBUG_API_PAYLOADS and idx <= MAX_DEBUG_API_PAYLOADS:
            self.write_debug_json(f"api_payload_{idx:03d}", {"source_url": source_url, "body": body})
    def write_article(self, article_index: int, record: ArticleRecord) -> Path:
        title_or_url = record.article.title or record.article.url or f"article-{article_index}"
        filename = f"{article_index:04d}_{slugify(title_or_url)}.json"
        path = self.articles_dir / filename
        path.write_text(json.dumps(record.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        self.index_payload["articles"].append({"index": article_index, "file": f"articles/{filename}", "url": record.article.url, "canonical_url": record.metadata.canonical_url, "title": record.article.title, "posted_date": record.article.posted_date, "author": record.article.author, "word_count": record.article.word_count, "score": record.quality.overall_score})
        self.index_payload["article_count"] = len(self.index_payload["articles"])
        self._write_index()
        return path
    def write_skipped_cached(self, url: str, reason: str = "already_cached") -> None:
        self.index_payload["skipped_cached"].append({"url": url, "reason": reason})
        self.index_payload["skipped_cached_count"] = len(self.index_payload["skipped_cached"])
        self._write_index()
    def write_rejected(self, url: str, reason: str, payload: Any | None = None) -> None:
        item = {"url": url, "reason": reason}
        if payload is not None:
            item["payload"] = payload
        self.index_payload["rejected"].append(item)
        self.index_payload["rejected_count"] = len(self.index_payload["rejected"])
        self._write_index()
