# Chronicle — Real‑time Event Clustering and Timeline Builder

[![CI](https://github.com/dukeblue1994-glitch/chronicle/actions/workflows/ci.yml/badge.svg)](https://github.com/dukeblue1994-glitch/chronicle/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/chronicle-events.svg)](https://pypi.org/project/chronicle-events/)
[![Python Versions](https://img.shields.io/pypi/pyversions/chronicle-events.svg)](https://pypi.org/project/chronicle-events/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> **Intelligent news aggregation powered by semantic embeddings, MinHash deduplication, and adaptive clustering algorithms.**

Chronicle is a production-ready event detection system that transforms noisy real-time news streams into coherent, clustered timelines. Built for scale and accuracy, it combines modern NLP techniques with robust ML pipelines to automatically discover trending topics and extract signal from noise.

## Architecture & Features

### 🧠 Advanced NLP Pipeline
- **Semantic Embeddings**: Sentence-Transformers (`all-MiniLM-L6-v2`) for high-quality vector representations
- **Intelligent Fallback**: Graceful degradation to TF-IDF when GPU resources unavailable
- **MinHash LSH Deduplication**: Sub-linear time complexity for near-duplicate detection (85% similarity threshold)
- **Extractive Summarization**: TF-IDF weighted sentence extraction for multi-document summaries

### 🔬 Adaptive Clustering
- **HDBSCAN**: Density-based clustering with automatic outlier detection and probabilistic membership scores
- **Agglomerative Fallback**: Distance-threshold clustering with cosine similarity for deterministic results
- **Dynamic Event Formation**: Minimum cluster size validation ensures signal over noise

### 🏗️ Production-Ready Design
- **Async I/O**: Non-blocking HTTP client for concurrent article fetching
- **Readability Extraction**: DOM-based content extraction with BeautifulSoup + lxml parsing
- **SQLite Storage**: Zero-config persistence with indexed queries for sub-millisecond lookups
- **FastAPI**: High-performance async REST API with automatic OpenAPI documentation
- **Docker Compose**: Single-command deployment with isolated collector and API services

## Installation

### From PyPI (coming soon)
```bash
pip install chronicle-events
```

### From GitHub
```bash
pip install git+https://github.com/dukeblue1994-glitch/chronicle.git
```

### For Development
```bash
git clone https://github.com/dukeblue1994-glitch/chronicle.git
cd chronicle
pip install -e ".[dev]"
```

## Quick Start

### Using as a Library
```python
from chronicle.nlp import encode
from chronicle.cluster import deduplicate, cluster_embeddings
from chronicle.timeline import summarize

# Your documents
docs = ["doc 1 text", "doc 2 text", ...]

# Deduplicate
rep_indices = deduplicate(docs, threshold=0.85)

# Embed and cluster
embeddings = encode(docs)
labels, probs = cluster_embeddings(embeddings, min_cluster_size=3)
```

### Running the Full Application

**Option 1: Docker Compose (Recommended)**
```bash
docker-compose up
# API available at http://localhost:8000/docs
```

**Option 2: Command Line Tools**
```bash
# Install package
pip install chronicle-events

# Start the collector (pulls HN every 60s)
chronicle-collector

# In another terminal, start the API
chronicle-api

# Or run clustering manually
chronicle-cluster
```

**Option 3: From Source**
```bash
git clone https://github.com/dukeblue1994-glitch/chronicle.git
cd chronicle
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start the collector
python apps/collector/run.py

# In another terminal, start the API
python apps/api/main.py

# Open API docs at http://127.0.0.1:8000/docs
```

## API Usage

### Endpoints

- `GET /events` — Current event clusters ranked by size and confidence, with extractive summaries
- `GET /events/{cluster_id}` — Detailed event view with all associated documents and metadata
- `GET /health` — System health check

### Example Response
```json
{
  "cluster_id": "ev-a3f5c9d2e1b8f4a6",
  "n_docs": 7,
  "score": 0.92,
  "summary": "New AI model achieves breakthrough performance...",
  "sample": [
    {"title": "GPT-5 Released", "url": "https://..."},
    {"title": "OpenAI Announces Major Update", "url": "https://..."}
  ]
}
```

## Technical Implementation

### Data Pipeline
1. **Ingestion**: Async fetcher polls Hacker News API every 60s (top 60 stories)
2. **Extraction**: Readability algorithm extracts clean article text from HTML
3. **Deduplication**: MinHash LSH identifies and filters near-duplicates in O(n) time
4. **Embedding**: Documents encoded to 384-dimensional semantic vectors
5. **Clustering**: HDBSCAN groups semantically similar documents with confidence scores
6. **Summarization**: TF-IDF ranks sentences across cluster for representative summary

### Algorithm Details
- **MinHash**: 128 permutations, 4-gram shingling, 0.85 Jaccard similarity threshold
- **HDBSCAN**: Min cluster size 3, Euclidean metric, probability-based membership
- **Embeddings**: Normalized L2 vectors for cosine similarity clustering
- **Summarization**: Top-k sentence selection by aggregate TF-IDF scores

## Notes

- **Storage**: SQLite at `data/chronicle.db` for zero-config portability
- **Embeddings**: Sentence-Transformers preferred; automatic TF-IDF fallback (4096 features, bigrams)
- **Clustering**: HDBSCAN when available; Agglomerative with 0.6 cosine distance threshold as fallback
- **Performance**: Batch processing of 400 recent documents with incremental clustering

## Data Source
- **Hacker News**: Top stories API with full article text extraction when available

## Configuration

Chronicle can be configured via environment variables. Copy `.env.example` to `.env` and customize:

```bash
# Key configuration options
CHRONICLE_COLLECTOR_INTERVAL=60  # Fetch interval in seconds
CHRONICLE_CLUSTER_MIN_SIZE=3     # Minimum documents per cluster
CHRONICLE_DEDUP_THRESHOLD=0.85   # Similarity threshold for deduplication
CHRONICLE_LOG_LEVEL=INFO         # Logging level
```

See `.env.example` for all available options.

## Development

### Setup
```bash
git clone https://github.com/dukeblue1994-glitch/chronicle.git
cd chronicle
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### Running Tests
```bash
pytest                    # Run all tests
pytest --cov             # With coverage
pytest tests/test_api.py # Specific test file
```

### Code Quality
```bash
black chronicle apps tests  # Format code
ruff check chronicle apps   # Lint code
mypy chronicle apps         # Type check
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Contribution Guide
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Run quality checks (`pytest && black . && ruff check .`)
5. Commit (`git commit -m 'Add amazing feature'`)
6. Push and create a Pull Request

## Roadmap

- [ ] Additional data sources (Reddit, Twitter, RSS)
- [ ] Real-time WebSocket API for live updates
- [ ] Event evolution tracking over time
- [ ] Advanced trend detection
- [ ] Grafana dashboards for monitoring
- [ ] Multi-language support

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Citation

If you use Chronicle in your research or project, please cite:

```bibtex
@software{chronicle2025,
  title = {Chronicle: Real-time Event Clustering and Timeline Builder},
  author = {Anderson, Nick},
  year = {2025},
  url = {https://github.com/dukeblue1994-glitch/chronicle}
}
```

## Acknowledgments

- Sentence-Transformers for embeddings
- HDBSCAN for density-based clustering
- MinHash LSH for efficient deduplication
- FastAPI for the API framework
- Hacker News for the data source

---

**Built with ❤️ for discovering what's trending in tech**
