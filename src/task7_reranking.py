"""Task 7 -- Reciprocal Rank Fusion (RRF)."""


def rerank_rrf(
    ranked_lists: list[list[dict]],
    top_k: int = 5,
    k: int = 60,
) -> list[dict]:
    """Fuse ranked lists by ID using sum(1 / (k + rank)), rank starting at 1."""
    if (
        not isinstance(top_k, int)
        or isinstance(top_k, bool)
        or top_k <= 0
    ):
        return []
    if not isinstance(k, int) or isinstance(k, bool) or k < 0:
        raise ValueError("RRF k must be a non-negative integer")

    scores: dict[str, float] = {}
    items: dict[str, dict] = {}
    first_seen: dict[str, int] = {}
    seen_order = 0

    for ranked_list in ranked_lists:
        seen_in_list: set[str] = set()
        for rank, item in enumerate(ranked_list, start=1):
            item_id = item.get("id")
            if not isinstance(item_id, str) or not item_id or item_id in seen_in_list:
                continue
            seen_in_list.add(item_id)
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
            if item_id not in items:
                items[item_id] = item
                first_seen[item_id] = seen_order
                seen_order += 1

    ranked_ids = sorted(
        scores, key=lambda item_id: (-scores[item_id], first_seen[item_id])
    )
    results: list[dict] = []
    for item_id in ranked_ids[:top_k]:
        source = items[item_id]
        results.append(
            {
                **source,
                "metadata": dict(source.get("metadata") or {}),
                "score": scores[item_id],
                "retrieval_method": "hybrid",
            }
        )
    return results


if __name__ == "__main__":
    print("Run pytest tests/test_contracts.py -q to verify RRF.")
