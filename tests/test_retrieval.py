"""Focused retrieval tests beyond the public assignment contracts."""

import pytest

from src.contracts import validate_search_results


def _metadata(index: int = 0) -> dict:
    return {
        "source": "danang.md",
        "title": "Da Nang",
        "doc_type": "news",
        "url": None,
        "chunk_index": index,
    }


def _result(item_id: str, score: float, method: str) -> dict:
    return {
        "id": item_id,
        "content": "Da Nang tourism content",
        "score": score,
        "metadata": _metadata(),
        "retrieval_method": method,
    }


def test_semantic_search_handles_invalid_top_k_without_embedding(monkeypatch):
    import src.task5_semantic_search as semantic

    monkeypatch.setattr(
        semantic,
        "embed_texts",
        lambda texts: pytest.fail("invalid search must not embed"),
    )
    assert semantic.semantic_search("Da Nang", top_k=0) == []
    assert semantic.semantic_search(" ", top_k=5) == []


def test_semantic_search_deduplicates_and_keeps_best_cosine(monkeypatch):
    import src.task5_semantic_search as semantic

    class Collection:
        def count(self):
            return 3

        def query(self, **kwargs):
            return {
                "ids": [["same", "same", "other"]],
                "documents": [["weak", "strong", "other"]],
                "metadatas": [[_metadata(), _metadata(), _metadata(1)]],
                "distances": [[0.4, 0.1, 0.2]],
            }

    monkeypatch.setattr(semantic, "embed_texts", lambda texts: [[0.1]])
    monkeypatch.setattr(semantic, "get_collection", lambda: Collection())
    output = semantic.semantic_search("Da Nang", top_k=3)
    assert [item["id"] for item in output] == ["same", "other"]
    assert output[0]["score"] == pytest.approx(0.9)
    assert output[0]["content"] == "strong"


def test_bm25_normalizes_vietnamese_case_and_deduplicates(monkeypatch):
    import src.task6_lexical_search as lexical

    monkeypatch.setattr(
        lexical,
        "CORPUS",
        [
            {"id": "one", "content": "  CẦU   Rồng Đà Nẵng ", "metadata": _metadata()},
            {"id": "one", "content": "Cầu Rồng", "metadata": _metadata(1)},
            {"id": "two", "content": "Bãi biển Mỹ Khê", "metadata": _metadata(2)},
        ],
    )
    monkeypatch.setattr(lexical, "_INDEX_CACHE_KEY", None)
    output = lexical.lexical_search("cầu rồng", top_k=5)
    assert [item["id"] for item in output] == ["one"]
    validate_search_results(output, top_k=5, expected_method="bm25")


def test_rrf_counts_duplicate_id_only_once_per_ranker():
    from src.task7_reranking import rerank_rrf

    dense_item = _result("same", 0.9, "dense")
    sparse_item = _result("same", 4.0, "bm25")
    output = rerank_rrf(
        [[dense_item, dense_item], [sparse_item]], top_k=2, k=60
    )
    assert len(output) == 1
    assert output[0]["score"] == pytest.approx(2 / 61)


def test_retrieve_without_reranking_returns_dense_only(monkeypatch):
    import src.task9_retrieval_pipeline as pipeline

    dense = [_result("dense", 0.9, "dense")]
    sparse = [_result("sparse", 9.0, "bm25")]
    monkeypatch.setattr(pipeline, "semantic_search", lambda query, top_k: dense)
    monkeypatch.setattr(pipeline, "lexical_search", lambda query, top_k: sparse)
    monkeypatch.setattr(
        pipeline,
        "rerank_rrf",
        lambda *args, **kwargs: pytest.fail("RRF must be disabled"),
    )
    output = pipeline.retrieve("Da Nang", use_reranking=False)
    assert output == dense


def test_pageindex_without_key_is_safe(monkeypatch):
    import src.task8_pageindex_vectorless as pageindex

    monkeypatch.setattr(pageindex, "PAGEINDEX_API_KEY", "")
    monkeypatch.delenv("PAGEINDEX_API_KEY", raising=False)
    assert pageindex.pageindex_search("Da Nang") == []


def test_pageindex_parses_cited_provider_result(monkeypatch):
    import src.task8_pageindex_vectorless as pageindex

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{"message": {"content": "Provider answer"}}],
                "citations": [
                    {
                        "doc_id": "pi-doc",
                        "file_name": "danang.pdf",
                        "page": 3,
                        "block": "p3_text_1",
                        "text": "My Khe is a beach in Da Nang.",
                    }
                ],
            }

    monkeypatch.setattr(pageindex, "_get_api_key", lambda: "test-key")
    monkeypatch.setattr(pageindex, "upload_documents", lambda: None)
    monkeypatch.setattr(
        pageindex,
        "_active_document",
        lambda: {"doc_id": "pi-doc", "file_name": "danang.pdf"},
    )
    monkeypatch.setattr(pageindex.requests, "post", lambda *args, **kwargs: Response())

    output = pageindex.pageindex_search("My Khe", top_k=2)
    validate_search_results(output, top_k=2, expected_method="pageindex")
    assert output[0]["content"] == "My Khe is a beach in Da Nang."
