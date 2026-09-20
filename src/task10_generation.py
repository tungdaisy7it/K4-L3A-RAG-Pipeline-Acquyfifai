"""Grounded answer generation with provider dispatch and citations."""

import logging
import os
from typing import Any

from dotenv import load_dotenv

from .task9_retrieval_pipeline import retrieve

LOGGER = logging.getLogger(__name__)
TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3
SAFE_REFUSAL = "Tôi không thể xác minh thông tin này từ nguồn hiện có."

SYSTEM_PROMPT = """Bạn là trợ lý thông tin du lịch Đà Nẵng.
Chỉ trả lời bằng bằng chứng trong CONTEXT. Không suy đoán, không dùng kiến thức bên ngoài.
Mỗi khẳng định quan trọng phải có citation dạng [C1], [C2] tương ứng với nhãn trong context.
Nếu context không đủ để trả lời, chỉ nói rằng bạn không thể xác minh từ nguồn hiện có.
Giữ nguyên tên riêng, số liệu và điều kiện như trong nguồn. Trả lời bằng tiếng Việt nếu người dùng hỏi tiếng Việt."""


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Place high-ranked chunks at the edges without mutating or losing IDs."""
    items = list(chunks)
    if len(items) <= 2:
        return items
    front: list[dict] = []
    back: list[dict] = []
    for index, chunk in enumerate(items):
        if index % 2 == 0:
            front.append(chunk)
        else:
            back.insert(0, chunk)
    return front + back


def format_context(chunks: list[dict]) -> str:
    """Render stable citation labels and source metadata for the model."""
    parts: list[str] = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata", {})
        title = metadata.get("title") or "Không rõ tiêu đề"
        source = metadata.get("source") or "Không rõ nguồn"
        url = metadata.get("url")
        url_label = f" | URL: {url}" if url else ""
        parts.append(
            f"[C{index}] ID: {chunk.get('id', '')} | Title: {title} | "
            f"Source: {source}{url_label}\n{chunk.get('content', '')}"
        )
    return "\n\n---\n\n".join(parts)


def _provider_config() -> tuple[str, str, str]:
    load_dotenv(override=False)
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    model = os.getenv("LLM_MODEL", "").strip()
    key_name = {"openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}.get(provider, "")
    return provider, model, os.getenv(key_name, "").strip() if key_name else ""


def _text_from_response(response: Any) -> str:
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()
    choices = getattr(response, "choices", None) or []
    if choices:
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if isinstance(content, str):
            return content.strip()
    content = getattr(response, "content", None) or []
    return "\n".join(str(getattr(item, "text", "")) for item in content).strip()


def call_llm(system_prompt: str, user_message: str) -> str:
    """Dispatch to the configured provider and return plain text."""
    provider, model, api_key = _provider_config()
    if provider not in {"openai", "gemini", "anthropic"}:
        raise RuntimeError(f"Unsupported LLM_PROVIDER: {provider}")
    if not api_key:
        raise RuntimeError(f"Missing API key for provider: {provider}")
    if not model:
        raise RuntimeError("LLM_MODEL is not configured")
    if provider == "openai":
        from openai import OpenAI
        response = OpenAI(api_key=api_key).chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
    elif provider == "gemini":
        from google import genai
        response = genai.Client(api_key=api_key).models.generate_content(
            model=model,
            contents=user_message,
            config={"system_instruction": system_prompt, "temperature": TEMPERATURE, "top_p": TOP_P},
        )
    else:
        from anthropic import Anthropic
        response = Anthropic(api_key=api_key).messages.create(
            model=model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=TEMPERATURE,
            max_tokens=1200,
        )
    text = _text_from_response(response)
    if not text:
        raise RuntimeError("LLM returned an empty response")
    return text


def _retrieval_source(chunks: list[dict]) -> str:
    methods = {item.get("retrieval_method") for item in chunks}
    if "pageindex" in methods:
        return "pageindex"
    return "hybrid" if methods else "none"


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Retrieve evidence, generate a grounded answer, and return its sources."""
    if not isinstance(query, str) or not query.strip() or not isinstance(top_k, int) or top_k <= 0:
        return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}
    try:
        chunks = retrieve(query, top_k=top_k)
    except Exception as exc:
        LOGGER.warning("Retrieval failed: %s", exc)
        return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}
    if not chunks:
        LOGGER.info("No evidence retrieved for query")
        return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}
    try:
        answer = call_llm(SYSTEM_PROMPT, f"CONTEXT:\n{format_context(reorder_for_llm(chunks))}\n\nQUESTION: {query.strip()}")
    except Exception as exc:
        LOGGER.warning("Generation provider failed: %s", exc)
        return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}
    return {"answer": answer, "sources": chunks, "retrieval_source": _retrieval_source(chunks)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(generate_with_citation("Bãi biển Mỹ Khê ở đâu?"))
