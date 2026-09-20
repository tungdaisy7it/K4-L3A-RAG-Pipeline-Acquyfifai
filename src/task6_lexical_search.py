"""Task 6 -- BM25 lexical search over the same chunks used by Task 4."""

import math
import re
import unicodedata
from collections import Counter

from .task4_chunking_indexing import chunk_documents, load_documents


CORPUS: list[dict] = []
_INDEX_CACHE_KEY: tuple | None = None
_INDEX_CACHE = None


def _tokenize(text: str) -> list[str]:
    """Normalize Unicode, case and whitespace while retaining Vietnamese words."""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    normalized = " ".join(normalized.split())
    return re.findall(r"[^\W_]+(?:[-'][^\W_]+)*", normalized, flags=re.UNICODE)


class _BM25Index:
    """BM25 using the positive Robertson/Lucene inverse document frequency."""

    def __init__(
        self,
        tokenized_corpus: list[list[str]],
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.k1 = k1
        self.b = b
        self.term_frequencies = [Counter(tokens) for tokens in tokenized_corpus]
        self.lengths = [len(tokens) for tokens in tokenized_corpus]
        self.average_length = (
            sum(self.lengths) / len(self.lengths) if self.lengths else 0.0
        )
        document_frequency: Counter[str] = Counter()
        for tokens in tokenized_corpus:
            document_frequency.update(set(tokens))
        corpus_size = len(tokenized_corpus)
        self.idf = {
            term: math.log(
                1.0 + (corpus_size - frequency + 0.5) / (frequency + 0.5)
            )
            for term, frequency in document_frequency.items()
        }

    def get_scores(self, query_tokens: list[str]) -> list[float]:
        if not self.term_frequencies or not query_tokens:
            return [0.0] * len(self.term_frequencies)

        scores: list[float] = []
        average_length = self.average_length or 1.0
        for frequencies, document_length in zip(self.term_frequencies, self.lengths):
            score = 0.0
            length_norm = self.k1 * (
                1.0 - self.b + self.b * document_length / average_length
            )
            for term in query_tokens:
                frequency = frequencies.get(term, 0)
                if frequency:
                    score += self.idf.get(term, 0.0) * (
                        frequency * (self.k1 + 1.0) / (frequency + length_norm)
                    )
            scores.append(score)
        return scores


def _get_corpus() -> list[dict]:
    global CORPUS
    if not CORPUS:
        CORPUS = chunk_documents(load_documents())
    return CORPUS


def build_bm25_index(corpus: list[dict]):
    """Build a BM25 index from Task 4 chunks."""
    return _BM25Index(
        [_tokenize(str(item.get("content", ""))) for item in corpus]
    )


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Return unique positive-score BM25 SearchResults in descending order."""
    if (
        not isinstance(query, str)
        or not query.strip()
        or not isinstance(top_k, int)
        or isinstance(top_k, bool)
        or top_k <= 0
    ):
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    corpus = _get_corpus()
    if not corpus:
        return []

    global _INDEX_CACHE_KEY, _INDEX_CACHE
    cache_key = (
        id(corpus),
        len(corpus),
        hash(tuple((item.get("id"), item.get("content")) for item in corpus)),
    )
    if cache_key != _INDEX_CACHE_KEY:
        _INDEX_CACHE = build_bm25_index(corpus)
        _INDEX_CACHE_KEY = cache_key

    scores = _INDEX_CACHE.get_scores(query_tokens)
    unique: dict[str, dict] = {}
    for item, raw_score in zip(corpus, scores):
        score = float(raw_score)
        item_id = item.get("id")
        if (
            score <= 0.0
            or not math.isfinite(score)
            or not isinstance(item_id, str)
            or not item_id
        ):
            continue
        result = {
            "id": item_id,
            "content": item["content"],
            "score": score,
            "metadata": dict(item["metadata"]),
            "retrieval_method": "bm25",
        }
        previous = unique.get(item_id)
        if previous is None or score > previous["score"]:
            unique[item_id] = result

    return sorted(
        unique.values(), key=lambda item: (-item["score"], item["id"])
    )[:top_k]


if __name__ == "__main__":
    for result in lexical_search("Cau Rong", top_k=3):
        print(result)
