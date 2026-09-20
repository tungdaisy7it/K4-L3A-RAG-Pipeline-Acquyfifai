"""Task 9 -- dense/BM25/RRF retrieval with PageIndex fallback."""

import os

from dotenv import load_dotenv

from .task5_semantic_search import semantic_search
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank_rrf
from .task8_pageindex_vectorless import pageindex_search


load_dotenv(override=False)

# Calibrated on the Da Nang tourism corpus; see the individual report.
DEFAULT_SCORE_THRESHOLD = 0.61
DEFAULT_TOP_K = 5


def _configured_threshold() -> float:
    """Read SCORE_THRESHOLD from .env, ignoring empty or malformed values."""
    raw = os.getenv("SCORE_THRESHOLD", "").strip()
    if not raw:
        return DEFAULT_SCORE_THRESHOLD
    try:
        return float(raw)
    except ValueError:
        return DEFAULT_SCORE_THRESHOLD


SCORE_THRESHOLD = _configured_threshold()


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = SCORE_THRESHOLD,
    use_reranking: bool = True,
) -> list[dict]:
    """Return hybrid/dense results, or PageIndex results for weak dense matches."""
    if (
        not isinstance(query, str)
        or not query.strip()
        or not isinstance(top_k, int)
        or isinstance(top_k, bool)
        or top_k <= 0
    ):
        return []

    candidate_count = top_k * 2
    dense = semantic_search(query, top_k=candidate_count)
    sparse = lexical_search(query, top_k=candidate_count)
    current = (
        rerank_rrf([dense, sparse], top_k=top_k)
        if use_reranking
        else dense[:top_k]
    )

    # Never compare the threshold with BM25 or RRF scores: they live on
    # unrelated scales. This is the original cosine score from Task 5.
    best_dense_score = max(
        (float(item["score"]) for item in dense), default=float("-inf")
    )
    if best_dense_score < score_threshold:
        try:
            fallback = pageindex_search(query, top_k=top_k)
        except Exception:
            fallback = []
        if fallback:
            return fallback[:top_k]

    return current[:top_k]


if __name__ == "__main__":
    for result in retrieve("Bai bien My Khe o dau?", top_k=3):
        print(result)
