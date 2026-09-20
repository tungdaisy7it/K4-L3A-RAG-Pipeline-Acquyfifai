# Báo cáo đóng góp cá nhân — Lê Thanh Tùng

## Thông tin

- Họ và tên: Lê Thanh Tùng
- Mã học viên: 2A202602499
- Nhóm: K4-L3A-RAG-Pipeline-Acquyfifai
- Repository/branch: `main`

## Phần việc đã thực hiện

| Module/deliverable | Việc trực tiếp làm | File/commit | Trạng thái |
|---|---|---|---|
| Generation và citation | Reorder không mutate, context có `[Ck]`, dispatch OpenAI/Gemini/Anthropic, safe refusal, GenerationResult | `src/task10_generation.py` | Done |
| Streamlit UI | Chatbot du lịch Đà Nẵng, hiển thị answer/source/title/URL/score, lưu session state | `app.py` | Done |
| Golden dataset | Bổ sung 15 câu có expected answer/context từ corpus | `group_project/evaluation/golden_dataset.json` | Done |
| Evaluation handoff | Ghi config A/B, threshold, metric status, worst-case checklist và hướng dẫn chạy thật | `group_project/evaluation/RESULT.md` | Done |
| Tài liệu | Viết lại hướng dẫn setup, `.env`, pipeline, test, demo và hạn chế | `README.md` | Done |

## Quyết định kỹ thuật

1. **Citation label ổn định:** context đánh nhãn `[C1]`, `[C2]` và giữ ID/title/source/URL của chunk. Lý do là answer có thể đối chiếu trực tiếp với `sources`; URL vắng mặt thì không bịa URL.
   **Trade-off:** prompt dài hơn nhưng dễ kiểm tra claim và hiển thị nguồn.

2. **Provider lỗi là safe refusal:** SDK được import lười, key/model đọc từ `.env` lúc gọi; thiếu cấu hình, retrieval lỗi hoặc response rỗng đều trả refusal và log cảnh báo không chứa secret.
   **Trade-off:** demo không có key không sinh câu trả lời, nhưng UI vẫn chạy và không tạo thông tin bịa.

## Kiểm thử và kết quả

- Đã đối chiếu contract generation/UI với `tests/test_contracts.py` và `tests/test_acceptance.py`.
- Golden dataset có 15 mẫu; RESULT ghi rõ A/B metric chưa đo nếu chưa có provider/evaluator thật.
- Demo query được ghi trong README gồm một câu domain, một exact-name và một câu ngoài domain.

## Hạn chế

- Chưa thể công bố điểm faithfulness/relevance/recall/precision nếu chưa chạy provider và evaluator thật; báo cáo không tự tạo số liệu.
- Một số PDF scan/bảng phức tạp có thể làm evidence bị thiếu.

## Xác nhận đóng góp

- Ngày: 20/09/2026
- Tên thành viên: Lê Thanh Tùng
