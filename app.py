"""Streamlit chat UI for the Da Nang tourism RAG assistant."""

import logging

import streamlit as st
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
SAFE_REFUSAL = "Tôi không thể xác minh thông tin này từ nguồn hiện có."

st.set_page_config(page_title="Tư vấn du lịch Đà Nẵng", page_icon="🌊", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = []


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
    st.title("Đà Nẵng RAG")
    st.caption("Trợ lý tư vấn thông tin và du lịch Đà Nẵng")
    top_k = st.slider("Số chunks truy hồi", 3, 10, 5)
    st.info("Câu trả lời chỉ dựa trên corpus đã lập chỉ mục và luôn kèm nguồn khi có bằng chứng.")

st.title("Chatbot tư vấn du lịch Đà Nẵng")
st.caption("Hỏi về địa điểm, lịch trình, văn hóa, ẩm thực và thông tin trong corpus.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            render_sources(message.get("sources", []), message.get("retrieval_source", "none"))

query = st.chat_input("Ví dụ: Cầu Rồng có điểm gì nổi bật?")
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
