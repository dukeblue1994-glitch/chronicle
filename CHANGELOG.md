# Changelog

All notable changes to Chronicle will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-10-02

### Added
- Event text search, source and publication-time filters, pagination, and latest sorting.
- Source-linked chronological timelines, corpus statistics, and database readiness endpoint.
- Offline demo and JSON corpus inspection through the `chronicle` CLI.
- Explicit TF-IDF and semantic embedding modes with actionable model-load errors.
- Python 3.13 and 3.14 CI coverage, installed-wheel demo verification, and gated PyPI publication.

### Fixed
- Legacy duplicate-document migrations blocked by foreign keys.
- Non-atomic migrations and batch assignment writes, stale noise assignments, and changed-document derived data.
- Singleton and fallback clusters violating minimum size, and zero vectors becoming events.
- Empty vocabulary failures in text encoding and extractive summaries.
- Unstable event IDs caused by batch-specific vector coordinates.
- API reload and worker startup, missing Docker scheduler, and mismatched publishing secret name.

### Changed
- Python 3.10 is the minimum supported version; Python 3.9 is no longer supported.
- Sentence Transformers is an optional extra so the default installation needs no model download.
- Event responses include source names and first/last publication timestamps.
- Database schema 3 adds cascading foreign keys and transactional upgrades.
- Public documentation describes implemented behavior and operational limits.

## [0.1.0] - 2025-11-07

### Added
- Initial release
- Real-time HN story collection
- MinHash LSH deduplication
- Semantic embeddings with Sentence-Transformers
- HDBSCAN clustering with fallback to Agglomerative
- Extractive summarization with TF-IDF
- FastAPI REST API
- SQLite database storage
- Docker and Docker Compose support
- CLI tools for collector, API, and clustering
- Python package distribution

### Features
- `/events` endpoint for clustered events
- `/events/{cluster_id}` endpoint for event details
- `/health` endpoint for health checks
- Async HTTP client for concurrent fetching
- Readability-based article extraction
- Automatic duplicate detection
- Probabilistic cluster membership
- Multi-document summarization

[0.2.0]: https://github.com/dukeblue1994-glitch/chronicle/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/dukeblue1994-glitch/chronicle/releases/tag/v0.1.0
