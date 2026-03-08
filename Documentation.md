# Adaptive Scraper Project

## What changed

This package refactors the original `scraper.py` into a modular project and adds immediate-ROI improvements:

- smarter selector mining for listing/article detection
- anti-bot heuristics and block-signal detection
- hydration state extraction from common JS bootstrapping blobs
- richer extraction pipeline using JSON-LD, OG/meta, Trafilatura, extruct, htmldate, readability, DOM fallback, and API payloads
- field-level provenance and confidence tracking
- richer output model with crawl metadata, quality signals, and extraction trace
- debug artifacts per run
- canonical URL based cache normalization

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
```

## Run

```bash
python run.py --website adevarul.ro --max-articles 10
python run.py --website hotnews.ro --force-rediscover
python run.py --website https://example.com/article/123 --force-page-type article
```

## Output

Each run writes into `output/<domain>_<timestamp>/`:

- `index.json`
- `site_config_snapshot.json`
- `articles/*.json`
- `debug/*.html|*.json`

## Immediate ROI additions

### Smarter selector detection
The scraper now mines listing and article container candidates by scoring DOM blocks on:

- number of article-like links
- headings density
- identity hints such as `feed`, `listing`, `story`, `article`, `content`
- paragraph count and text density
- negative signals such as `footer`, `nav`, `cookie`, `sidebar`

### Anti-bot
The refactor adds:

- request jitter
- stealth-like browser headers on static requests
- resource blocking in Playwright for images/fonts/media/trackers
- challenge detection for Cloudflare, Akamai, DataDome, CAPTCHA-like responses, and suspicious HTTP codes like 403/429/503

### Richer data
The output now contains:

- `crawl` metadata: final URL, status code, fetch latency, fetch timestamp
- `quality` scores: title/content/date/author score, overall score, paywall/live hints
- `trace` metadata: source per field, confidence per field, anti-bot signals, hydration/api usage

## Notes

This is intentionally still pragmatic, not a huge framework. The next logical step would be:

- persistent Playwright browser/context pool
- bounded concurrency
- optional proxy layer
- stronger comment extraction
- domain plugin hooks
- metrics/exporters
