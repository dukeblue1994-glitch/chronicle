from __future__ import annotations

import re
from typing import Dict, List

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


def summarize(docs: List[Dict], max_sentences: int = 3) -> str:
    if max_sentences <= 0:
        return ""
    texts = [d.get("text") or d.get("title") or "" for d in docs]
    joined = " ".join(texts)
    sents = re.split(r"(?<=[.!?])\s+", joined)
    if len(sents) <= max_sentences:
        return " ".join(sents[:max_sentences]).strip()
    try:
        vec = TfidfVectorizer(max_features=2048).fit(sents)
    except ValueError:
        return " ".join(sents[:max_sentences]).strip()
    X = vec.transform(sents).toarray()
    scores = X.sum(axis=1)
    idx = np.argsort(scores)[::-1][:max_sentences]
    idx.sort()
    return " ".join([sents[i] for i in idx]).strip()
