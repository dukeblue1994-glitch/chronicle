# Changelog

All notable changes to Chronicle will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive test suite with pytest
- GitHub Actions CI/CD pipeline
- Configuration management with Pydantic Settings
- Environment variable support via .env files
- Type checking with mypy
- Code formatting with Black
- Linting with Ruff
- Test coverage reporting
- PyPI publishing workflow

### Changed
- Improved dependency specifications with version ranges
- Removed unused dependencies (pandas, prometheus-client)
- Enhanced README with installation instructions
- Organized requirements by category

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

[Unreleased]: https://github.com/dukeblue1994-glitch/chronicle/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/dukeblue1994-glitch/chronicle/releases/tag/v0.1.0
