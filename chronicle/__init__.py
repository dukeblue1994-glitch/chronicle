"""Chronicle - Intelligent event detection and clustering system."""

__version__ = "0.1.0"

from chronicle.cluster.algos import cluster_embeddings, deduplicate
from chronicle.nlp.embedding import encode
from chronicle.timeline.summarize import summarize

__all__ = ["encode", "deduplicate", "cluster_embeddings", "summarize"]
