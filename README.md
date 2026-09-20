# Chatbot RAG du lịch Đà Nẵng

Dự án xây dựng trợ lý hỏi đáp về du lịch Đà Nẵng. Corpus gồm tài liệu pháp lý/quy hoạch trong `data/standardized/legal/` và bài giới thiệu địa điểm, lịch trình, văn hóa, ẩm thực trong `data/standardized/news/`. Mỗi câu trả lời có thể truy ngược về chunk, tiêu đề, source và URL.

## Cài đặt

```bash
python -m venv .venv
.\.venv\Scripts\activate       # Windows
python -m pip install -e ".[dev]"
copy .env.example .env
```

Điền cấu hình cục bộ trong `.env`:

```dotenv
LLM_PROVIDER=openai
LLM_MODEL=<model-name>
OPENAI_API_KEY=<local-secret>
EMBEDDING_PROVIDER=sentence_transformers
EMBEDDING_MODEL=BAAI/bge-m3
SCORE_THRESHOLD=0.61
```

Có thể thay `LLM_PROVIDER` bằng `gemini` hoặc `anthropic`, với key tương ứng. Không đưa API key vào README, git hoặc log.

## Chạy pipeline

```bash
python -m src.task1_collect_legal_docs
python -m src.task2_crawl_news
python -m src.task3_convert_markdown
python -m src.task4_chunking_indexing
streamlit run app.py
```

Retrieval dùng dense search, BM25 và RRF; fallback PageIndex là tùy chọn. Generation dùng `src/task10_generation.py`, reorder chunk không làm đổi ID, format context có nhãn `[C1]`, `[C2]` và prompt yêu cầu chỉ dùng evidence.

## Test và evaluation

```bash
pytest tests/test_contracts.py -q
pytest tests/test_acceptance.py -q
pytest -q
```

Golden set có 15 case tại `group_project/evaluation/golden_dataset.json`. Báo cáo A/B dense-only và hybrid + RRF nằm tại `group_project/evaluation/RESULT.md`. Chỉ điền điểm metric sau khi chạy thật với cùng model, prompt, dataset và `top_k`; không dùng số ước đoán.

## Demo tối thiểu

- Query trong domain: `Bãi biển Mỹ Khê có gì nổi bật?`
- Query exact name: `My Son Sanctuary được gọi chính xác bằng tên gì?`
- Query ngoài domain: `Cách sửa kernel panic trên Linux?`

UI lưu cả answer và sources trong `st.session_state`, nên citation vẫn hiện sau rerun. Khi retrieval/provider lỗi hoặc evidence không đủ, hệ thống trả safe refusal thay vì làm Streamlit crash.

## Hạn chế

Corpus phụ thuộc chất lượng crawl và trích xuất PDF; tài liệu scan/bảng phức tạp có thể thiếu text. Chất lượng câu trả lời phụ thuộc embedding, top-k, threshold và provider. Thông tin du lịch có thể thay đổi, vì vậy không nên xem chatbot là nguồn xác nhận thời gian mở cửa, giá vé hoặc quy định hiện hành nếu corpus chưa cập nhật.
