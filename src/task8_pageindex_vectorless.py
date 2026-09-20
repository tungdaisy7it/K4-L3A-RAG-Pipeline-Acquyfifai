"""Task 8 -- fault-tolerant PageIndex vectorless fallback.

The cloud API currently accepts PDF documents. The standardized Markdown
corpus is therefore bundled into one cached PDF before upload. The returned
document ID is cached by a content fingerprint so unchanged data is never
uploaded twice.
"""

import hashlib
import json
import logging
import os
import re
import time
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv()

LOGGER = logging.getLogger(__name__)
PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
PAGEINDEX_API_URL = os.getenv("PAGEINDEX_API_URL", "https://api.pageindex.ai").rstrip("/")
REQUEST_TIMEOUT = (5, 45)
PROCESS_TIMEOUT_SECONDS = 45

ROOT_DIR = Path(__file__).parent.parent
STANDARDIZED_DIR = ROOT_DIR / "data" / "standardized"
CACHE_PATH = ROOT_DIR / "pageindex_doc_ids.json"
PDF_CACHE_DIR = ROOT_DIR / "pageindex_pdfs"


def _get_api_key() -> str:
    # Read the environment on every call so deployments can inject the key
    # after importing the module. The module constant remains easy to patch.
    return (os.getenv("PAGEINDEX_API_KEY") or PAGEINDEX_API_KEY).strip()


def _source_files() -> list[Path]:
    return sorted(path for path in STANDARDIZED_DIR.rglob("*.md") if path.is_file())


def _corpus_fingerprint(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(STANDARDIZED_DIR).as_posix().encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        digest.update(b"\0")
    return digest.hexdigest()


def _load_cache() -> dict:
    try:
        payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _save_cache(payload: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = CACHE_PATH.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(CACHE_PATH)


def _font_path() -> Path | None:
    candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/calibri.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
    ]
    return next((path for path in candidates if path.exists()), None)


def _build_corpus_pdf(paths: list[Path], fingerprint: str) -> Path:
    """Create a deterministic local PDF accepted by the PageIndex cloud API."""
    from fpdf import FPDF

    PDF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    output = PDF_CACHE_DIR / f"danang-tourism-{fingerprint[:16]}.pdf"
    if output.exists() and output.stat().st_size > 0:
        return output

    font_path = _font_path()
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    if font_path:
        pdf.add_font("CorpusFont", fname=str(font_path))
        font_name = "CorpusFont"
    else:
        font_name = "Helvetica"

    for path in paths:
        relative = path.relative_to(STANDARDIZED_DIR).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        # PDF control characters are invalid and very long runs are difficult
        # for line wrappers. Markdown structure and Vietnamese diacritics stay.
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
        if not font_path:
            text = text.encode("latin-1", errors="replace").decode("latin-1")

        pdf.add_page()
        pdf.set_font(font_name, size=14)
        pdf.multi_cell(0, 7, f"SOURCE: {relative}")
        pdf.ln(2)
        pdf.set_font(font_name, size=9)
        pdf.set_x(pdf.l_margin)
        try:
            pdf.multi_cell(0, 4.5, text, wrapmode="CHAR")
        except TypeError:  # Compatibility with older fpdf2 versions.
            pdf.multi_cell(0, 4.5, text)

    pdf.output(str(output))
    return output


def _wait_until_ready(doc_id: str, headers: dict[str, str]) -> bool:
    deadline = time.monotonic() + PROCESS_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        response = requests.get(
            f"{PAGEINDEX_API_URL}/doc/{doc_id}/metadata",
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        status = str(response.json().get("status", "")).casefold()
        if status in {"completed", "complete", "ready", "success", "succeeded"}:
            return True
        if status in {"failed", "error", "cancelled"}:
            return False
        time.sleep(2)
    return False


def upload_documents() -> None:
    """Upload the corpus once and cache its PageIndex document ID.

    Missing credentials and all provider/local conversion failures are treated
    as an unavailable optional fallback, not as fatal application errors.
    """
    api_key = _get_api_key()
    paths = _source_files()
    if not api_key or not paths:
        return

    try:
        fingerprint = _corpus_fingerprint(paths)
        cache = _load_cache()
        documents = cache.get("documents", {})
        existing = documents.get(fingerprint) if isinstance(documents, dict) else None
        if isinstance(existing, dict) and existing.get("doc_id"):
            return

        pdf_path = _build_corpus_pdf(paths, fingerprint)
        headers = {"api_key": api_key}
        with pdf_path.open("rb") as handle:
            response = requests.post(
                f"{PAGEINDEX_API_URL}/doc/",
                headers=headers,
                files={"file": (pdf_path.name, handle, "application/pdf")},
                timeout=REQUEST_TIMEOUT,
            )
        response.raise_for_status()
        payload = response.json()
        doc_id = payload.get("doc_id")
        if not isinstance(doc_id, str) or not doc_id:
            raise ValueError("PageIndex upload response did not contain doc_id")

        cache = {
            "schema_version": 1,
            "active_fingerprint": fingerprint,
            "documents": {
                **(documents if isinstance(documents, dict) else {}),
                fingerprint: {
                    "doc_id": doc_id,
                    "file_name": pdf_path.name,
                    "source_count": len(paths),
                },
            },
        }
        _save_cache(cache)
        _wait_until_ready(doc_id, headers)
    except (OSError, ValueError, TypeError, requests.RequestException) as exc:
        LOGGER.warning("PageIndex upload unavailable: %s", exc)


def _active_document() -> dict | None:
    paths = _source_files()
    if not paths:
        return None
    fingerprint = _corpus_fingerprint(paths)
    cache = _load_cache()
    documents = cache.get("documents", {})
    entry = documents.get(fingerprint) if isinstance(documents, dict) else None
    return entry if isinstance(entry, dict) and entry.get("doc_id") else None


def _response_content(payload: dict) -> str:
    choices = payload.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content", "") if isinstance(message, dict) else ""
    return content.strip() if isinstance(content, str) else ""


def _response_citations(payload: dict) -> list[dict]:
    citations = payload.get("citations")
    if not isinstance(citations, list):
        choices = payload.get("choices") or []
        message = choices[0].get("message", {}) if choices else {}
        citations = message.get("citations", []) if isinstance(message, dict) else []
    return [item for item in citations if isinstance(item, dict)]


def _citation_content(
    citation: dict,
    doc_id: str,
    headers: dict[str, str],
    page_cache: dict[int, str],
) -> str:
    for key in ("text", "quote", "content", "markdown"):
        value = citation.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    block_id = citation.get("block") or citation.get("block_id")
    if block_id:
        response = requests.get(
            f"{PAGEINDEX_API_URL}/doc/{doc_id}/block/{block_id}/",
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        text = response.json().get("text", "")
        if isinstance(text, str) and text.strip():
            return text.strip()

    page = citation.get("page") or citation.get("page_index")
    try:
        page_number = int(page)
    except (TypeError, ValueError):
        return ""
    if page_number not in page_cache:
        response = requests.get(
            f"{PAGEINDEX_API_URL}/doc/{doc_id}/",
            headers=headers,
            params={"type": "ocr", "format": "page"},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        result = response.json().get("result", [])
        if isinstance(result, list):
            for item in result:
                if not isinstance(item, dict):
                    continue
                try:
                    item_page = int(item.get("page_index"))
                except (TypeError, ValueError):
                    continue
                markdown = item.get("markdown", "")
                if isinstance(markdown, str):
                    page_cache[item_page] = markdown.strip()
    return page_cache.get(page_number, "")


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Return PageIndex SearchResults, or an empty list when unavailable."""
    if (
        not isinstance(query, str)
        or not query.strip()
        or not isinstance(top_k, int)
        or isinstance(top_k, bool)
        or top_k <= 0
        or not _get_api_key()
    ):
        return []

    try:
        upload_documents()
        entry = _active_document()
        if not entry:
            return []

        api_key = _get_api_key()
        doc_id = str(entry["doc_id"])
        headers = {"api_key": api_key, "Content-Type": "application/json"}
        response = requests.post(
            f"{PAGEINDEX_API_URL}/chat/completions",
            headers=headers,
            json={
                "doc_id": doc_id,
                "messages": [{"role": "user", "content": query.strip()}],
                "stream": False,
                "enable_citations": True,
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        answer = _response_content(payload)
        citations = _response_citations(payload)

        results: list[dict] = []
        seen: set[str] = set()
        page_cache: dict[int, str] = {}
        for rank, citation in enumerate(citations, start=1):
            cited_doc_id = str(citation.get("doc_id") or doc_id)
            block = citation.get("block") or citation.get("block_id")
            page = citation.get("page") or citation.get("page_index")
            result_id = f"pageindex:{cited_doc_id}:{block or page or rank}"
            if result_id in seen:
                continue
            content = _citation_content(citation, cited_doc_id, headers, page_cache)
            if not content:
                content = answer
            if not content:
                continue
            seen.add(result_id)
            source = str(
                citation.get("doc")
                or citation.get("document")
                or citation.get("file_name")
                or entry.get("file_name")
                or "pageindex"
            )
            results.append(
                {
                    "id": result_id,
                    "content": content,
                    "score": 1.0 / rank,
                    "metadata": {
                        "source": source,
                        "title": source,
                        "doc_type": "news",
                        "url": None,
                        "chunk_index": rank - 1,
                        "page": page,
                        "block_id": block,
                    },
                    "retrieval_method": "pageindex",
                }
            )
            if len(results) >= top_k:
                break

        if not results and answer:
            results.append(
                {
                    "id": f"pageindex:{doc_id}:answer",
                    "content": answer,
                    "score": 1.0,
                    "metadata": {
                        "source": str(entry.get("file_name") or "pageindex"),
                        "title": "PageIndex response",
                        "doc_type": "news",
                        "url": None,
                        "chunk_index": 0,
                    },
                    "retrieval_method": "pageindex",
                }
            )
        return results[:top_k]
    except (OSError, ValueError, TypeError, requests.RequestException) as exc:
        LOGGER.warning("PageIndex search unavailable: %s", exc)
        return []


if __name__ == "__main__":
    for result in pageindex_search("Bai bien My Khe co gi noi bat?", top_k=3):
        print(result)
