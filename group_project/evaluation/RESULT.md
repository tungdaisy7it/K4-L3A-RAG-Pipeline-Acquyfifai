# Kết quả đánh giá RAG du lịch Đà Nẵng

> **Trạng thái bàn giao:** Pipeline, contract tests, acceptance tests và UI demo đã chạy được. Các điểm A/B của bốn metric generation chưa được điền vì môi trường bàn giao chưa có LLM provider/model; báo cáo giữ nguyên trạng thái chưa đo để tránh tạo số liệu không có bằng chứng.

## Tóm tắt cho demo

- **Corpus:** 44 tài liệu Markdown du lịch/pháp lý Đà Nẵng, embedding `BAAI/bge-m3`.
- **Retrieval:** dense-only cho Config A; dense + BM25 + RRF cho Config B; `top_k=5`.
- **Generation:** prompt grounded, citation `[C1]...`, safe refusal khi thiếu evidence hoặc provider lỗi.
- **Đã kiểm chứng:** `27 passed` bằng `.venv`; Streamlit khởi động thành công ở cổng demo cục bộ.
- **Cần chạy bổ sung:** cấu hình `.env` cục bộ rồi chạy cùng golden set 15 câu để lấy faithfulness, answer relevance, context recall và context precision.

## Overall scores

### Run information

| Trường | Giá trị |
|---|---|
| Ngày ghi nhận | 2026-09-20 |
| Framework/version | Ragas 0.4.3 (đã khai báo trong `pyproject.toml`); chưa hoàn tất lần chạy evaluator có generator thật |
| Evaluator model | Chưa cấu hình |
| Generator model | Chưa cấu hình (`LLM_MODEL` để trống trong môi trường bàn giao) |
| Embedding model | `BAAI/bge-m3` |
| Corpus version/commit | `4178d12` (commit retrieval gần nhất trong repo; cần ghi lại commit chứa corpus khi chạy chính thức) |
| Golden dataset size | 15 |
| `top_k` | 5 |
| Fallback threshold/calibration | `0.61`; midpoint đo được `0.611638`, balanced accuracy 100% trên pool calibration 353 chunks theo báo cáo retrieval |

### Configurations

- **Config A — dense-only:** `retrieve(..., use_reranking=False)`, giữ cùng `top_k`, threshold, prompt và generator.
- **Config B — hybrid + RRF:** `retrieve(..., use_reranking=True)`, dense + BM25 hợp nhất một lần bằng RRF.

Hai cấu hình đã được định nghĩa trong pipeline. Lần chạy A/B với LLM/evaluator thật chưa được thực hiện vì `.env` bàn giao không có provider key/model; do đó không dùng số giả để kết luận metric.

| Metric | Config A | Config B | Delta B−A |
|---|---:|---:|---:|
| Faithfulness | Chưa đo | Chưa đo | Chưa tính |
| Answer relevance | Chưa đo | Chưa đo | Chưa tính |
| Context recall | Chưa đo | Chưa đo | Chưa tính |
| Context precision | Chưa đo | Chưa đo | Chưa tính |
| **Average** | Chưa đo | Chưa đo | Chưa tính |

Latency và cost cũng chưa được ghi nhận vì chưa có lần gọi provider thật. Retrieval calibration ở trên là evidence cho threshold, không phải điểm A/B generation.

## A/B comparison

- **Cấu hình tốt hơn:** Chưa thể kết luận bằng bốn metric khi chưa chạy cùng generator/evaluator.
- **Evidence hiện có:** Config B có thêm tín hiệu BM25/RRF và phù hợp với truy vấn tên riêng; Config A có đường chạy dense-only riêng để đối chứng. Đây là nhận định thiết kế, không phải kết quả điểm số.
- **Trade-off latency/cost:** Config B thực hiện thêm lexical search và RRF; chi phí LLM dự kiến giữ nguyên vì cùng context budget, nhưng latency thực tế cần đo bằng cùng batch.

## Worst performers

Chưa có output per-case từ evaluator, nên bảng dưới ghi rõ các ca cần kiểm tra thay vì bịa điểm số.

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause cần xác minh |
|---:|---|---|---:|---:|---:|---:|---|---|
| 1 | Tên riêng “My Son Sanctuary” | A/B | Chưa đo | Chưa đo | Chưa đo | Chưa đo | retrieval | Đối chiếu dense với BM25 cho exact keyword và title `article_07`. |
| 2 | Lịch trình Đà Nẵng 3 ngày 2 đêm | A/B | Chưa đo | Chưa đo | Chưa đo | Chưa đo | retrieval/generation | Câu tổng hợp có thể cần nhiều chunk từ `article_21`; kiểm tra recall và citation map. |
| 3 | Câu hỏi ngoài miền về Linux/kernel panic | A/B | Chưa đo | Chưa đo | Chưa đo | Chưa đo | generation/safety | Kiểm tra threshold, refusal và việc không biến fallback yếu thành câu trả lời khẳng định. |

## Recommendations

| Ưu tiên | Cải tiến | Evidence hiện có | Tác động kỳ vọng | Cách kiểm chứng |
|---:|---|---|---|---|
| 1 | Chạy evaluator thật với một provider/model cố định và lưu output từng case | Bốn metric hiện chưa có số đo | Có baseline A/B hợp lệ | Chạy cùng 15 cases, prompt, `top_k=5`, model và seed; lưu JSON kết quả. |
| 2 | Bổ sung exact-name queries và đo riêng recall của BM25/RRF | Golden set có My Son Sanctuary, 2298/QĐ và Sơn Trà | Giảm lỗi tên riêng/chính sách | So sánh hit@5 của A và B, kiểm tra ID nguồn trong context. |
| 3 | Thêm kiểm thử citation validator và refusal ngoài miền | Contract mới chỉ kiểm tra schema | Giảm claim không có evidence | Assert mọi `[Ck]` trong answer map được tới source, và OOD trả refusal khi evidence yếu. |
| 4 | Đo latency/cost theo từng stage | Chưa có log benchmark provider | Biết trade-off thực tế của hybrid | Ghi timer retrieval, provider latency, token usage cho cùng batch A/B. |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
|---|---|---:|---:|---|
| Reranking nâng cao | Chưa chạy | Chưa đo | Chưa đo | Không đủ evidence để báo cáo bonus. |

## Hướng dẫn chạy lần đánh giá chính thức

1. Cấu hình `LLM_PROVIDER`, `LLM_MODEL` và key trong `.env` cục bộ; không commit secret.
2. Chạy hai cấu hình trên cùng `group_project/evaluation/golden_dataset.json`, cùng prompt và `top_k=5`.
3. Ghi output JSON, phiên bản model/corpus, latency và token cost; sau đó thay các ô “Chưa đo” bằng số lấy trực tiếp từ run.
