# Chronicle

**Turn a news stream into events you can search, inspect, and follow.**

[![CI](https://github.com/dukeblue1994-glitch/chronicle/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/dukeblue1994-glitch/chronicle/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/chronicle-events?color=2563eb)](https://pypi.org/project/chronicle-events/)
[![Python](https://img.shields.io/pypi/pyversions/chronicle-events)](https://pypi.org/project/chronicle-events/)
[![License](https://img.shields.io/badge/license-MIT-0f766e)](LICENSE)

Chronicle is a Python library and local service for grouping related news into source-linked event timelines. It collects Hacker News stories, removes near-duplicate headlines, clusters related documents, and exposes extractive summaries through a typed API.

Built and maintained by [Nick Anderson](https://github.com/dukeblue1994-glitch).

```text
COLLECT             DISTILL             ORGANIZE             EXPLORE
Hacker News   -->   MinHash + text  -->  Event clusters  -->  Search + timelines
Article text        TF-IDF / semantic   SQLite persistence   FastAPI + Python
```

## What is new in 0.2

| Capability | What it gives you |
| --- | --- |
| Searchable events | Text search, source and date filters, pagination, and latest-first sorting |
| Source-linked timelines | Publication-ordered documents, timestamps, and links for each event |
| Reproducible local demo | Twelve clearly labeled sample documents, no network or model download |
| Consistent clustering | Minimum-size rules on both clustering backends; empty vectors stay noise |
| Safer persistence | Transactional migrations and batch assignment updates, cascading foreign keys, and stale-assignment cleanup |
| Release verification | Python 3.10-3.14 tests, Linux/macOS/Windows coverage, dependency audit, and installed-wheel checks |

## Install

Requires Python 3.10 or newer. The default installation works on CPU and uses TF-IDF when the optional semantic model is unavailable.

```bash
python -m pip install chronicle-events
```

For semantic embeddings, install the optional extra. The first use downloads the configured model.

```bash
python -m pip install "chronicle-events[embeddings]"
```

Choose a backend with `CHRONICLE_EMBEDDING_BACKEND`: `auto` tries the optional model and falls back to TF-IDF, `tfidf` stays local, and `semantic` reports an error if the model cannot load.

## Try it without collecting live data

```bash
chronicle demo --db data/chronicle-demo.db
```

This creates a new demo database and groups fictional space, energy, and ocean reports. Existing files are never overwritten. The command prints corpus statistics as JSON.

Point the API at that database and start it:

```bash
# macOS / Linux
export CHRONICLE_DB_PATH=data/chronicle-demo.db
chronicle-api
```

```powershell
# PowerShell
$env:CHRONICLE_DB_PATH = "data/chronicle-demo.db"
chronicle-api
```

Open [the API explorer](http://127.0.0.1:8000/docs). Try `/events?sort_by=latest`, then use an event ID with `/events/{cluster_id}/timeline`.

## Collect live news

Run these in separate terminals with the same database configuration:

```bash
chronicle-collector  # Collect Hacker News stories and article text
chronicle-scheduler  # Rebuild event assignments every five minutes
chronicle-api        # Serve the API on port 8000
```

For a single clustering pass, use `chronicle-cluster`. Inspect the corpus with `chronicle stats`.

Docker Compose starts all three services and stores data in a named volume:

```bash
docker compose up --build
```

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /events` | Search and browse event summaries |
| `GET /events/{cluster_id}` | Retrieve an event and its documents |
| `GET /events/{cluster_id}/timeline` | Read its documents in publication order |
| `GET /stats` | Corpus size, source counts, and schema version |
| `GET /health` | Process liveness and package version |
| `GET /ready` | Database availability and schema readiness |
| `GET /docs` | Interactive OpenAPI documentation |

`/events` accepts `q`, `source`, `since`, `until`, `limit`, `offset`, `min_docs`, and `sort_by=size|score|latest`. Dates are Unix timestamps. All document filters must match the same document; the returned summary retains the full event context.

```bash
curl 'http://127.0.0.1:8000/events?q=space&sort_by=latest&limit=10'
```

The API is intended for local use or deployment behind your own access controls. It does not provide authentication or a public hosting service.

## Use the library

```python
from chronicle import cluster_embeddings, deduplicate, encode, summarize

texts = [
    "A lunar spacecraft enters orbit around the moon.",
    "Engineers confirm lunar spacecraft orbit ahead of landing.",
    "The lunar mission prepares for its moon landing.",
]
representatives = deduplicate(texts)
vectors = encode(texts)
labels, scores = cluster_embeddings(vectors, min_cluster_size=3)
summary = summarize([{"text": text} for text in texts], max_sentences=2)
```

HDBSCAN may classify a small or weakly separated batch entirely as noise. A label of `-1` means no event assignment. TF-IDF vectors are fitted per batch and should not be compared across separate `encode` calls. HDBSCAN scores describe cluster membership; fallback scores are assignment indicators, not calibrated probabilities.

## Configuration

All settings use the `CHRONICLE_` prefix. See [.env.example](https://github.com/dukeblue1994-glitch/chronicle/blob/main/.env.example).

| Setting | Default | Purpose |
| --- | --- | --- |
| `CHRONICLE_DB_PATH` | `data/chronicle.db` | Shared SQLite database |
| `CHRONICLE_EMBEDDING_BACKEND` | `auto` | `auto`, `tfidf`, or `semantic` |
| `CHRONICLE_CLUSTER_BATCH_SIZE` | `400` | Recent documents processed per pass |
| `CHRONICLE_CLUSTER_MIN_SIZE` | `3` | Minimum representative documents per event |
| `CHRONICLE_CLUSTER_SCHEDULE` | `300` | Seconds between clustering passes |
| `CHRONICLE_DEDUP_THRESHOLD` | `0.85` | Token-set Jaccard threshold for LSH candidates |
| `CHRONICLE_LOG_FORMAT` | `text` | `text` or structured `json` |

Event IDs are derived from sorted document identities, so repeated processing of the same membership preserves the ID. A membership change produces a new ID. Timelines describe publication order, not historical revisions of an event. Chronicle currently processes bounded recent batches rather than maintaining an unbounded streaming model.

## Upgrading from 0.1

1. Use Python 3.10 or newer. Python 3.9 is no longer supported.
2. Stop the collector, scheduler, and API, then back up the SQLite database.
3. Upgrade the package and restart the services. Database migrations run automatically in a transaction.

Where a legacy database contains duplicate `(source, external_id)` pairs, the newest document row is retained and obsolete derived vectors and assignments are removed. The next clustering pass rebuilds assignments. Rows without source identity are retained.

## Development

```bash
python -m pip install -e ".[dev]" build twine
ruff check chronicle apps tests
black --check chronicle apps tests
mypy chronicle apps
pytest
python -m build
twine check --strict dist/*
```

See [CONTRIBUTING.md](https://github.com/dukeblue1994-glitch/chronicle/blob/main/CONTRIBUTING.md) and the [release guide](https://github.com/dukeblue1994-glitch/chronicle/blob/main/PUBLISH.md).

## License and credits

[MIT](https://github.com/dukeblue1994-glitch/chronicle/blob/main/LICENSE). Chronicle builds on FastAPI, scikit-learn, HDBSCAN, datasketch, Sentence Transformers, and the Hacker News API.
