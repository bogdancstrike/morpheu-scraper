from __future__ import annotations
from adaptive_scraper.detectors.anti_bot import likely_liveblog, likely_paywalled
from adaptive_scraper.models import ArticleRecord
from adaptive_scraper.utils.common import article_fingerprint

def score_record(record: ArticleRecord, html: str | None = None) -> ArticleRecord:
    wc = record.article.word_count or 0
    title_score = 1.0 if record.article.title else 0.0
    content_score = min(1.0, wc / 600) if wc else 0.0
    date_score = 1.0 if record.article.posted_date else 0.0
    author_score = 1.0 if record.article.author else 0.0
    overall = round((title_score * 0.25) + (content_score * 0.45) + (date_score * 0.15) + (author_score * 0.15), 4)
    record.quality.title_score = title_score
    record.quality.content_score = round(content_score, 4)
    record.quality.date_score = date_score
    record.quality.author_score = author_score
    record.quality.overall_score = overall
    record.quality.likely_paywalled = likely_paywalled(html or "")
    record.quality.likely_liveblog = likely_liveblog(record.article.title, html or "")
    record.trace.field_sources.setdefault("fingerprint", article_fingerprint(record.article.title, record.article.content, record.article.posted_date, record.article.source))
    return record

def article_has_enough_content(record: ArticleRecord, min_words: int) -> bool:
    return bool(record.article.title) and (record.article.word_count or 0) >= min_words
