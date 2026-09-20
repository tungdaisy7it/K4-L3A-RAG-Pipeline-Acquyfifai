"""Task 5 -- dense semantic search over the Task 4 Chroma collection."""

import math

from .task4_chunking_indexing import embed_texts, get_collection


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """Return unique dense SearchResults ordered by cosine similarity."""
    if (
        not isinstance(query, str)
        or not query.strip()
        or not isinstance(top_k, int)
        or isinstance(top_k, bool)
        or top_k <= 0
    ):
        return []

    vectors = embed_texts([query.strip()])
    if not vectors or not vectors[0]:
        return []

    collection = get_collection()
    n_results = top_k
    count = getattr(collection, "count", None)
    if callable(count):
        corpus_size = count()
        if corpus_size <= 0:
            return []
        n_results = min(n_results, corpus_size)

    response = collection.query(
        query_embeddings=[vectors[0]],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    def first_row(key: str) -> list:
        rows = response.get(key) or []
        return rows[0] if rows and rows[0] is not None else []

    unique: dict[str, dict] = {}
    for item_id, content, metadata, distance in zip(
        first_row("ids"),
        first_row("documents"),
        first_row("metadatas"),
        first_row("distances"),
    ):
        if not isinstance(item_id, str) or not item_id or not isinstance(content, str):
            continue
        try:
            cosine_similarity = 1.0 - float(distance)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(cosine_similarity):
            continue

        # Cosine similarity is theoretically in [-1, 1]. Preserve negative
        # matches instead of disguising them as zero.
        cosine_similarity = max(-1.0, min(1.0, cosine_similarity))
        result = {
            "id": item_id,
            "content": content,
            "score": cosine_similarity,
            "metadata": dict(metadata or {}),
            "retrieval_method": "dense",
        }
        previous = unique.get(item_id)
        if previous is None or result["score"] > previous["score"]:
            unique[item_id] = result

    return sorted(
        unique.values(), key=lambda item: (-item["score"], item["id"])
    )[:top_k]


if __name__ == "__main__":
    for result in semantic_search("du lich Da Nang", top_k=3):
        print(result)
