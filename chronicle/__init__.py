"""Chronicle - Intelligent event detection and clustering system."""

__version__ = "0.1.0"

from chronicle.nlp.embedding import encode
from chronicle.cluster.algos import deduplicate, cluster_embeddings
from chronicle.timeline.summarize import summarize

__all__ = ["encode", "deduplicate", "cluster_embeddings", "summarize"]
