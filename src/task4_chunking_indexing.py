"""
Task 4 — Chunking, embedding và indexing.

Hướng dẫn:
    1. Đọc toàn bộ Markdown trong data/standardized/.
    2. Chia văn bản bằng strategy đã chọn.
    3. Embed chunks bằng một provider duy nhất.
    4. Upsert vào ChromaDB với cosine distance.

Mỗi document/chunk phải theo docs/MODULE_CONTRACTS.md. ID cần ổn định để
chạy lại pipeline không tạo dữ liệu trùng. Task 5 phải dùng chung embed_texts().
"""

import json
import re
import sys
from pathlib import Path

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

# Fix Windows cp1252 console encoding
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# Giải thích lựa chọn tham số trong báo cáo nhóm.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM = 1024

COLLECTION_NAME = "rag_documents"

# Batch size for embedding and upserting (avoid memory issues)
EMBED_BATCH_SIZE = 64
UPSERT_BATCH_SIZE = 5000

# Singleton model cache
_model_cache = None


def _get_model() -> SentenceTransformer:
    """Load and cache the embedding model (singleton)."""
    global _model_cache
    if _model_cache is None:
        print(f"Loading embedding model: {EMBEDDING_MODEL} ...")
        _model_cache = SentenceTransformer(EMBEDDING_MODEL)
    return _model_cache


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts using sentence-transformers.

    This function is shared between Task 4 (indexing) and Task 5 (search).
    """
    model = _get_model()
    embeddings = model.encode(
        texts,
        batch_size=EMBED_BATCH_SIZE,
        show_progress_bar=len(texts) > 10,
        normalize_embeddings=True,
    )
    return embeddings.tolist()


def get_collection():
    """Mở Chroma collection dùng cosine distance."""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def _extract_metadata_from_md(content: str, path: Path) -> dict:
    """Extract title and URL from the Markdown header metadata."""
    title = path.stem
    url = None

    # Try to extract title from first heading
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()

    # Try to extract source URL
    url_match = re.search(r"\*\*Source:\*\*\s*(https?://\S+)", content)
    if url_match:
        url = url_match.group(1).strip()

    return {"title": title, "url": url}


def load_documents() -> list[dict]:
    """Đọc Markdown và trả về danh sách Document."""
    documents = []

    for subdir in ["legal", "news"]:
        dir_path = STANDARDIZED_DIR / subdir
        if not dir_path.exists():
            print(f"  [WARN] Directory not found: {dir_path}")
            continue

        doc_type = subdir  # "legal" or "news"

        for path in sorted(dir_path.glob("*.md")):
            content = path.read_text(encoding="utf-8").strip()
            if not content or len(content) < 200:
                print(f"  [SKIP] Too short: {path.name} ({len(content)} chars)")
                continue

            # Extract metadata from Markdown content
            meta = _extract_metadata_from_md(content, path)

            doc_id = f"{subdir}/{path.name}"
            documents.append({
                "id": doc_id,
                "content": content,
                "metadata": {
                    "source": path.name,
                    "title": meta["title"],
                    "doc_type": doc_type,
                    "url": meta["url"],
                },
            })

    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id và chunk_index."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = []
    for document in documents:
        texts = splitter.split_text(document["content"])
        for index, text in enumerate(texts):
            if not text.strip():
                continue
            chunks.append({
                "id": f"{document['id']}::chunk-{index}",
                "content": text,
                "metadata": {
                    **document["metadata"],
                    "chunk_index": index,
                },
            })

    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk."""
    texts = [chunk["content"] for chunk in chunks]
    vectors = embed_texts(texts)
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector
    return chunks


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB."""
    collection = get_collection()

    # Upsert in batches to avoid memory issues
    for i in range(0, len(chunks), UPSERT_BATCH_SIZE):
        batch = chunks[i:i + UPSERT_BATCH_SIZE]
        collection.upsert(
            ids=[chunk["id"] for chunk in batch],
            documents=[chunk["content"] for chunk in batch],
            embeddings=[chunk["embedding"] for chunk in batch],
            metadatas=[chunk["metadata"] for chunk in batch],
        )
        print(f"  Upserted batch {i // UPSERT_BATCH_SIZE + 1} "
              f"({len(batch)} chunks)")


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    print("=== Loading documents ===")
    documents = load_documents()
    print(f"  Loaded {len(documents)} documents")

    legal_count = sum(1 for d in documents if d["metadata"]["doc_type"] == "legal")
    news_count = sum(1 for d in documents if d["metadata"]["doc_type"] == "news")
    print(f"  Legal: {legal_count}, News: {news_count}")

    print("\n=== Chunking documents ===")
    chunks = chunk_documents(documents)
    print(f"  Created {len(chunks)} chunks")

    print("\n=== Embedding chunks ===")
    embedded_chunks = embed_chunks(chunks)
    print(f"  Embedded {len(embedded_chunks)} chunks "
          f"(dim={len(embedded_chunks[0]['embedding']) if embedded_chunks else 0})")

    print("\n=== Indexing to ChromaDB ===")
    index_to_vectorstore(embedded_chunks)

    # Verify
    collection = get_collection()
    print(f"\n=== Done ===")
    print(f"  ChromaDB collection: {COLLECTION_NAME}")
    print(f"  Total chunks in DB: {collection.count()}")
    print(f"  Database path: {CHROMA_DIR}")


if __name__ == "__main__":
    run_pipeline()
