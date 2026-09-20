"""Streamlit chat UI for the Da Nang tourism RAG assistant."""

import logging
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
SAFE_REFUSAL = "Tôi không thể xác minh thông tin này từ nguồn hiện có."

ROOT = Path(__file__).parent
STANDARDIZED_DIR = ROOT / "data" / "standardized"

st.set_page_config(
    page_title="Tư vấn du lịch Đà Nẵng",
    page_icon="🌊",
    layout="wide",
)

st.markdown(
    """
    <style>
    .hero { padding: 1.4rem 1.6rem; border-radius: 1rem; background: linear-gradient(120deg, #075985, #0f766e); color: white; margin-bottom: 1rem; }
    .hero h1 { margin: 0; font-size: 2rem; }
    .hero p { margin: .35rem 0 0; opacity: .9; }
    .status-card { padding: .8rem 1rem; border: 1px solid #dbeafe; border-radius: .75rem; background: #f8fafc; min-height: 5rem; }
    .status-label { color: #64748b; font-size: .78rem; text-transform: uppercase; letter-spacing: .04em; }
    .status-value { color: #0f172a; font-weight: 650; font-size: 1rem; margin-top: .25rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_query" not in st.session_state:
    st.session_state.pending_query = ""


def render_sources(sources: list[dict], retrieval_source: str) -> None:
    if not sources:
        st.info("Chưa có đủ bằng chứng trong corpus để trả lời câu hỏi này.")
        return
    st.caption(f"Phương thức retrieval: `{retrieval_source}` · {len(sources)} nguồn")
    with st.expander("Nguồn và citation", expanded=False):
        for index, source in enumerate(sources, 1):
            metadata = source.get("metadata", {})
            title = metadata.get("title", "Không rõ tiêu đề")
            label = f"[C{index}] {title} · score={float(source.get('score', 0)):.4f}"
            st.markdown(f"**{label}**")
            st.caption(f"Source: {metadata.get('source', 'Không rõ nguồn')}")
            if metadata.get("url"):
                st.markdown(f"URL: {metadata['url']}")


def run_generation(query: str, top_k: int) -> dict:
    """Load retrieval/generation dependencies only when a query is submitted."""
    from src.task10_generation import generate_with_citation

    return generate_with_citation(query, top_k)


with st.sidebar:
    st.title("🌊 Đà Nẵng RAG")
    st.caption("Bảng điều khiển demo hệ thống")
    top_k = st.slider("Số chunks truy hồi", 3, 10, 5)
    provider = os.getenv("LLM_PROVIDER", "chưa cấu hình")
    model = os.getenv("LLM_MODEL", "chưa cấu hình")
    corpus_count = len(list(STANDARDIZED_DIR.rglob("*.md"))) if STANDARDIZED_DIR.exists() else 0
    st.divider()
    st.caption("Cấu hình hiện tại")
    st.code(f"provider: {provider}\nmodel: {model}\ntop_k: {top_k}", language="text")
    if st.button("🧹 Xoá lịch sử", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    st.caption("Câu trả lời chỉ dựa trên corpus đã lập chỉ mục và luôn kèm nguồn khi có bằng chứng.")

st.markdown(
    '<div class="hero"><h1>Chatbot tư vấn du lịch Đà Nẵng</h1>'
    '<p>Hỏi về địa điểm, lịch trình, văn hóa và ẩm thực — câu trả lời có citation từ corpus.</p></div>',
    unsafe_allow_html=True,
)

status_columns = st.columns(4)
status = [
    ("Provider", provider),
    ("Embedding", os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")),
    ("Corpus", f"{corpus_count} tài liệu Markdown"),
    ("Retrieval", "Dense + BM25 + RRF"),
]
for column, (label, value) in zip(status_columns, status):
    column.markdown(
        f'<div class="status-card"><div class="status-label">{label}</div>'
        f'<div class="status-value">{value}</div></div>',
        unsafe_allow_html=True,
    )

st.subheader("Demo nhanh")
demo_columns = st.columns(3)
demo_queries = [
    "Bãi biển Mỹ Khê có gì nổi bật?",
    "My Son Sanctuary được gọi chính xác bằng tên gì?",
    "Cách sửa kernel panic trên Linux?",
]
for column, demo_query in zip(demo_columns, demo_queries):
    if column.button(demo_query, use_container_width=True):
        st.session_state.pending_query = demo_query

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            render_sources(message.get("sources", []), message.get("retrieval_source", "none"))

query = st.chat_input("Ví dụ: Cầu Rồng có điểm gì nổi bật?") or st.session_state.pending_query
st.session_state.pending_query = ""
if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)
    with st.chat_message("assistant"):
        try:
            result = run_generation(query, top_k)
        except Exception:
            logging.exception("Unexpected UI generation failure")
            result = {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}
        st.session_state.messages.append({
            "role": "assistant",
            "content": result["answer"],
            "sources": result.get("sources", []),
            "retrieval_source": result.get("retrieval_source", "none"),
        })
        st.markdown(result["answer"])
        render_sources(result.get("sources", []), result.get("retrieval_source", "none"))
