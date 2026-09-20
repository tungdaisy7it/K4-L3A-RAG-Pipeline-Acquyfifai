# Báo cáo đóng góp cá nhân — Retrieval và fallback

## Thông tin

- Họ và tên: Đinh Quốc Bảo
- Mã học viên: 2A202602933
- Nhóm: Acquyfifai
- Repository/branch: `tungdaisy7it/K4-L3A-RAG-Pipeline-Acquyfifai` / `main`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit | Trạng thái |
|---|---|---|---|
| Dense retrieval | Embed query bằng Task 4, query Chroma cosine, đổi distance thành similarity, dedupe/sort/giới hạn `top_k` | `src/task5_semantic_search.py` / `ff497ac` | Done |
| BM25 retrieval | Nạp đúng Task 4 chunks, tokenize Unicode tiếng Việt, BM25 có cache, lọc score không dương và ID trùng | `src/task6_lexical_search.py` / `ff497ac` | Done |
| RRF | Fuse theo ID bằng `sum(1/(k+rank))`, không trộn trực tiếp cosine/BM25 | `src/task7_reranking.py` / `ff497ac` | Done |
| PageIndex fallback | Đọc key từ môi trường, bundle/cache corpus PDF và `doc_id`, timeout, parse citation, fail-safe | `src/task8_pageindex_vectorless.py` / `ff497ac` | Done |
| Retrieval pipeline | Dense + BM25, RRF đúng một lần, dense-only A/B, fallback theo dense cosine gốc | `src/task9_retrieval_pipeline.py` / `ff497ac` | Done |
| Retrieval tests | Kiểm tra edge cases, dedupe, tiếng Việt, PageIndex thiếu key/provider response và dense-only | `tests/test_retrieval.py` / `ff497ac` | Done |

## Quyết định kỹ thuật quan trọng

1. **Fallback chỉ dùng best dense cosine score gốc.**
   **Lý do/evidence:** BM25 và RRF có thang đo khác cosine; so sánh chúng với cùng threshold sẽ không có ý nghĩa. Pipeline lưu riêng `dense` và lấy `max(item["score"])` trước khi quyết định PageIndex.
   **Trade-off:** Query có tên riêng mạnh ở BM25 nhưng semantic yếu vẫn có thể thử PageIndex; nếu provider không sẵn sàng, pipeline giữ kết quả hybrid thay vì crash.

2. **PageIndex là provider tùy chọn và fail-safe.**
   **Lý do/evidence:** Không có key, timeout, HTTP lỗi hoặc response không hợp lệ đều trả `[]`; cache được khóa theo SHA-256 của toàn corpus để không upload lại dữ liệu không đổi.
   **Trade-off:** Lần đầu phải chuyển Markdown thành PDF và chờ provider xử lý; bản fallback không thay thế dense/hybrid khi provider rỗng.

## Hiệu chỉnh threshold

Model/corpus: `BAAI/bge-m3`, cosine similarity, 44 tài liệu và 5.540 chunks. Do
Chroma cache từ Người 1 không có trong workspace và full CPU re-index cần gần 4
giờ, calibration dùng pool 353 chunks: BM25 top-20 của mỗi query cộng 3 chunks
phân tầng (đầu/giữa/cuối) từ mỗi document. Tất cả score bên dưới vẫn được tính
bằng chính `embed_texts()` của Task 4; BM25 chỉ chọn candidate, không tham gia
threshold.

| Nhóm | Query | Best dense cosine |
|---|---|---:|
| In | Bãi biển Mỹ Khê có gì nổi bật? | 0.658920 |
| In | Cầu Rồng phun lửa vào thời gian nào? | 0.685928 |
| In | Bán đảo Sơn Trà có những điểm tham quan nào? | 0.699016 |
| In | Món mì Quảng Đà Nẵng có đặc trưng gì? | 0.724534 |
| In | Gợi ý lịch trình du lịch Đà Nẵng 3 ngày 2 đêm | 0.781310 |
| In | Danh thắng Ngũ Hành Sơn nằm ở đâu? | 0.716283 |
| Out | Cách sửa lỗi kernel panic trên Linux? | 0.432278 |
| Out | Giá cổ phiếu NVIDIA hôm nay là bao nhiêu? | 0.380003 |
| Out | Hướng dẫn giải phương trình vi phân bậc hai | 0.450013 |
| Out | Đội tuyển nào vô địch World Cup 2018? | 0.429316 |
| Out | Công thức làm bánh macaron kiểu Pháp? | 0.542189 |
| Out | Cách chăm sóc mèo Anh lông ngắn? | 0.564356 |

Chọn `SCORE_THRESHOLD = 0.61`, nằm giữa `max(out)=0.564356` và
`min(in)=0.658920`. Midpoint tối ưu đo được là `0.611638`; threshold 0.61 đạt
balanced accuracy 100% trên tập calibration này. Người 3 nên chạy lại cùng 12
query trên full Chroma index trước khi chốt evaluation report.

## Kiểm thử và kết quả

- Retrieval contract subset: `6 passed` (`semantic_search`, `lexical_search`, RRF và `retrieve`).
- Test bổ sung: `7 passed` trong `tests/test_retrieval.py`.
- Manual BM25 query `Cầu Rồng phun lửa`: top scores `28.5322`, `27.3299`, `24.7912`; cả ba kết quả là bài du lịch Đà Nẵng và đủ schema.
- Manual out-of-domain query `Cách sửa lỗi kernel panic trên Linux?`: PageIndex không có key trả `[]`; pipeline giữ 3 kết quả `hybrid` hợp lệ thay vì crash.
- Full `tests/test_contracts.py`: retrieval pass; còn một lỗi ngoài phạm vi tại Task 10 vì `reorder_for_llm()` chưa được triển khai.
- Acceptance: 3/5 pass; hai lỗi ngoài phạm vi là golden dataset rỗng và evaluation report còn `TODO`.
- PageIndex live không được gọi vì môi trường không có `PAGEINDEX_API_KEY`; nhánh thiếu key và provider response/error đã được kiểm thử bằng mock.

## Điều còn hạn chế

- PageIndex cloud cần key/quota để kiểm thử live; hiện chỉ xác minh contract và fail-safe không gọi mạng.
- Threshold hiện dựa trên candidate pool 353/5.540 chunks vì full Chroma cache chưa được bàn giao; cần xác nhận lại trên full index.
- Nếu có thêm thời gian, ưu tiên chạy calibration trên tập query lớn hơn và theo dõi ROC/PR thay vì một tập nhỏ cân bằng.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc mình thực hiện và có thể chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Đinh Quốc Bảo
