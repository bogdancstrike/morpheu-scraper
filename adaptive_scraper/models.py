from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

@dataclass
class Comment:
    author: Optional[str] = None
    content: Optional[str] = None
    posted_date: Optional[str] = None
    likes: Optional[int] = None
    dislikes: Optional[int] = None
    replies_count: Optional[int] = None

@dataclass
class Publisher:
    name: Optional[str] = None
    url: Optional[str] = None
    logo: Optional[str] = None

@dataclass
class Article:
    url: Optional[str] = None
    title: Optional[str] = None
    subtitle: Optional[str] = None
    author: Optional[str] = None
    authors: Optional[List[str]] = None
    posted_date: Optional[str] = None
    updated_date: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    language: Optional[str] = None
    word_count: Optional[int] = None
    reading_time_minutes: Optional[int] = None
    section: Optional[str] = None
    source: Optional[str] = None
    article_type: Optional[str] = None
    paywalled: Optional[bool] = None
    liveblog: Optional[bool] = None

@dataclass
class Engagement:
    likes: Optional[int] = None
    shares: Optional[int] = None
    comments_count: Optional[int] = None
    views: Optional[int] = None

@dataclass
class Metadata:
    tags: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    images: Optional[List[str]] = None
    videos: Optional[List[str]] = None
    canonical_url: Optional[str] = None
    keywords: Optional[List[str]] = None
    top_image: Optional[str] = None
    related_links: List[str] = field(default_factory=list)
    inline_links: List[str] = field(default_factory=list)
    publisher: Optional[Publisher] = None

@dataclass
class CrawlMetadata:
    discovered_from: Optional[str] = None
    discovered_anchor_text: Optional[str] = None
    referrer_url: Optional[str] = None
    response_status: Optional[int] = None
    final_url: Optional[str] = None
    fetched_at_epoch: Optional[int] = None
    fetch_latency_ms: Optional[int] = None

@dataclass
class QualitySignals:
    content_score: Optional[float] = None
    title_score: Optional[float] = None
    date_score: Optional[float] = None
    author_score: Optional[float] = None
    duplicate_score: Optional[float] = None
    likely_paywalled: bool = False
    likely_liveblog: bool = False
    likely_gallery: bool = False
    overall_score: Optional[float] = None

@dataclass
class ExtractionTrace:
    field_sources: Dict[str, str] = field(default_factory=dict)
    field_confidence: Dict[str, float] = field(default_factory=dict)
    fetch_method: Optional[str] = None
    page_type_detected: Optional[str] = None
    static_fetch_succeeded: bool = False
    browser_fetch_succeeded: bool = False
    api_intercept_used: bool = False
    hydration_used: bool = False
    extraction_warnings: List[str] = field(default_factory=list)
    block_signals: List[str] = field(default_factory=list)

@dataclass
class ArticleRecord:
    article: Article
    engagement: Engagement
    comments: List[Comment]
    metadata: Metadata
    crawl: CrawlMetadata = field(default_factory=CrawlMetadata)
    quality: QualitySignals = field(default_factory=QualitySignals)
    trace: ExtractionTrace = field(default_factory=ExtractionTrace)
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class FetchResult:
    html: str
    final_url: str
    status_code: Optional[int]
    headers: Dict[str, Any]
    latency_ms: int
    method: str
    block_signals: List[str] = field(default_factory=list)

@dataclass
class BrowserPageData:
    rendered_html: str
    final_url: str
    status_code: Optional[int]
    latency_ms: int
    title: Optional[str] = None
    anchors: List[dict] = field(default_factory=list)
    api_cards: List[dict] = field(default_factory=list)
    best_api_text: Optional[str] = None
    best_api_text_score: int = 0
    api_patterns: List[str] = field(default_factory=list)
    hydration_data: List[dict] = field(default_factory=list)
    hydration_keys: List[str] = field(default_factory=list)
    block_signals: List[str] = field(default_factory=list)
