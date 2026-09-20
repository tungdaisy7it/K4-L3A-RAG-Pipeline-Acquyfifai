# Individual contribution report

Báo cáo đóng góp cá nhân của thành viên phụ trách phần Dữ liệu & Indexing (Người 1).

---

## Thông tin

- Họ và tên: Nguyễn Thu Hằng
- Mã học viên: 2A202602463
- Nhóm: Acquyfifai
- Repository/branch: `tungdaisy7it/K4-L3A-RAG-Pipeline-Acquyfifai` / `main`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| **Task 1: Thu thập tài liệu pháp lý** | Viết script thu thập, kiểm tra và tải 5 văn bản pháp lý/quy hoạch du lịch Đà Nẵng (Quy hoạch Sơn Trà, QĐ 2298, Dự thảo TT13...) định dạng PDF vào thư mục landing. | `src/task1_collect_legal_docs.py`, `data/landing/legal/*.pdf` | Done |
| **Task 2: Thu thập tin tức & cẩm nang du lịch** | Xây dựng crawler dùng `requests` + `BeautifulSoup` trích xuất 39 bài viết du lịch Đà Nẵng từ `danangfantasticity.com`, bóc tách metadata (`url`, `title`, `date_crawled`, `content_markdown`) vào JSON. | `src/task2_crawl_news.py`, `data/landing/news/*.json` | Done |
| **Task 3: Chuẩn hóa Markdown** | Xây dựng pipeline trích xuất văn bản từ PDF (dùng `pypdf`) và parser tin tức, chuẩn hóa 44 tài liệu sang Markdown kèm YAML frontmatter chuẩn (`source`, `title`, `doc_type`, `url`, `date_crawled`). | `src/task3_convert_markdown.py`, `data/standardized/legal/*.md`, `data/standardized/news/*.md` | Done |
| **Task 4: Chunking, Embedding & Indexing** | Xây dựng pipeline đọc tài liệu chuẩn hóa, chia đoạn bằng `RecursiveCharacterTextSplitter` (size=512, overlap=64), nhúng vector bằng model `BAAI/bge-m3` và lưu trữ/upsert vào ChromaDB. | `src/task4_chunking_indexing.py`, `chroma_db/` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Sử dụng `RecursiveCharacterTextSplitter` với `chunk_size=512` và `chunk_overlap=64` cho toàn bộ tài liệu (cả pháp lý lẫn tin tức).  
   **Lý do/evidence:** Văn bản pháp lý và cẩm nang du lịch có cấu trúc phân tầng tự nhiên (tiêu đề, điều khoản, đoạn văn). Bộ chia đệ quy ưu tiên ngắt theo đoạn `\n\n`, sau đó đến dòng `\n`, rồi câu `. ` giúp đảm bảo tính trọn vẹn ngữ nghĩa của mỗi chunk. Kích thước 512 ký tự vừa vặn với khả năng tiếp nhận của embedding model và giữ ngữ cảnh tập trung, overlap 64 ký tự tránh mất thông tin ở điểm giao cắt giữa hai chunk.  
   **Trade-off:** Số lượng chunk tạo ra nhiều hơn so với chunking kích thước lớn (1000+ ký tự), đòi hỏi nhiều tài nguyên tính toán hơn khi sinh embedding và dung lượng lưu trữ vector store tăng nhẹ, nhưng bù lại tăng độ nhạy và chính xác khi truy vấn semantic search.

2. **Quyết định:** Sử dụng mô hình embedding đa ngôn ngữ `BAAI/bge-m3` dùng chung cho cả giai đoạn indexing (Task 4) và retrieval (Task 5).  
   **Lý do/evidence:** Tập dữ liệu du lịch Đà Nẵng bao gồm cả tiếng Việt và tiếng Anh, đồng thời chứa cả thuật ngữ hành chính/pháp lý lẫn văn phong du lịch đời thường. Model `bge-m3` có khả năng biểu diễn ngữ nghĩa đa ngôn ngữ vượt trội, hỗ trợ context length lên tới 8192 token và tương thích tốt với pipeline RAG tiếng Việt.  
   **Trade-off:** Model có kích thước tương đối lớn (~2.2GB), cần bộ nhớ RAM và thời gian tải/khởi tạo ban đầu lớn hơn các model lightweight như `all-MiniLM-L6-v2`.

## Kiểm thử và kết quả

- **Test hoặc query tôi đã dùng:**
  - `pytest tests/test_acceptance.py -k "test_corpus or test_standardized"`: Kiểm tra số lượng tối thiểu và tính hợp lệ của corpus landing & standardized.
  - `pytest tests/test_contracts.py -k "test_document or test_chunk or test_public_function_signatures"`: Kiểm tra contract interface của `load_documents`, `chunk_documents`, schema metadata và tính bất biến của dữ liệu.
  - Chạy thực tế end-to-end các module: `python -m src.task1_collect_legal_docs`, `python -m src.task2_crawl_news`, `python -m src.task3_convert_markdown`, `python -m src.task4_chunking_indexing`.
- **Kết quả trước/sau nếu có:**
  - *Trước:* Thư mục dữ liệu trống/chưa đủ điều kiện; hàm chunking và indexing ném `NotImplementedError`; test acceptance báo thiếu tài liệu.
  - *Sau:* Thu thập thành công 5 văn bản pháp lý (PDF) và 39 bài viết tin tức (JSON); chuẩn hóa 100% (44 file Markdown); tạo thành công các chunk đạt chuẩn metadata contract; upsert đầy đủ vào ChromaDB; 100% acceptance tests và contract tests của phần Dữ liệu & Indexing đều **PASSED**.
- **Lỗi đã phát hiện và cách xử lý:**
  - *Lỗi Windows DLL với `grpcio`:* Khi khởi tạo ChromaDB trên Windows gặp lỗi `DLL load failed while importing _cygrpc`. Đã khắc phục bằng cách cài đặt phiên bản ổn định `grpcio==1.62.3`.
  - *Lỗi trang PDF rỗng:* Một số trang trong tài liệu pháp lý là bản scan ảnh không có text layer, `pypdf` trả về chuỗi rỗng. Đã bổ sung logic kiểm tra độ dài text và fallback log cảnh báo để tránh sinh file Markdown rỗng.

## Điều còn hạn chế

- **Một hạn chế cụ thể của phần tôi làm:** Việc trích xuất PDF bằng `pypdf` hiện tại chủ yếu lấy text tuần tự, chưa tái tạo hoàn hảo định dạng bảng biểu phức tạp và chưa có OCR đối với các tài liệu scan hoàn toàn bằng hình ảnh.
- **Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện:** Tích hợp pipeline OCR và trích xuất bảng biểu chuyên sâu (như `pdfplumber` hoặc `MinerU`/`PaddleOCR`) để xử lý các phụ lục quy hoạch và bảng giá dịch vụ du lịch chi tiết hơn.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Nguyễn Thu Hằng
