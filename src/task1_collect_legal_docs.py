"""
Task 1 — Thu thập tài liệu chính sách/quy định.

Hướng dẫn:
    1. Chọn chủ đề của nhóm.
    2. Tìm tối thiểu 3 tài liệu PDF/DOCX từ nguồn công khai.
    3. Lưu file gốc vào data/landing/legal/.
    4. Đặt tên không dấu và thể hiện đúng nội dung.

Ví dụ tài liệu: học phí, học bổng, ký túc xá, quy trình đăng ký.
Nếu website chặn crawler, hãy chọn nguồn công khai khác; không vượt WAF.
"""

import sys
from pathlib import Path

import requests

# Fix Windows cp1252 console encoding for Vietnamese filenames
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"

# Danh sach tai lieu chinh sach du lich Da Nang tu nguon cong khai
# Cac file nay da duoc tai thu cong vao thu muc data/landing/legal/
# Script nay ho tro tai tu dong neu file chua co
LEGAL_SOURCES = {
    # Quyet dinh phe duyet de an phat trien du lich Da Nang
    "2298-qd-signed.pdf": {
        "description": "Quyet dinh 2298/QD-UBND phe duyet de an phat trien du lich Da Nang",
        "manual": True,  # File da duoc tai thu cong
    },
    # Cac van de bao ton ban dao Son Tra
    "110517_cacvande_SonTra.pdf": {
        "description": "Cac van de bao ton va phat trien ban dao Son Tra",
        "manual": True,
    },
    # Van ban bai bao nghien cuu ve du lich Da Nang
    "2112-van-ban-bai-bao-du-lich.pdf": {
        "description": "Van ban nghien cuu ve phat trien du lich Da Nang",
        "manual": True,
    },
    # Du thao to trinh ban hanh quy dinh du lich
    "du-thao-to-trinh-ban-hanh-quy-dinh.pdf": {
        "description": "Du thao to trinh de nghi ban hanh quy dinh du lich",
        "manual": True,
    },
    # Du thao quyet dinh thuc hien thong tu 13
    "du-thao-quyet-dinh-thuc-hien-TT13.pdf": {
        "description": "Du thao quyet dinh thuc hien Thong tu 13 ve du lich",
        "manual": True,
    },
}

# URLs cong khai co the tai truc tiep (backup)
DOWNLOADABLE_SOURCES = {
    # Luat Du lich 2017 - Van ban phap luat cong khai
    "luat-du-lich-2017.pdf": "https://luatvietnam.vn/van-hoa/luat-du-lich-2017-115518-d1.html",
}


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def check_existing_files() -> list[Path]:
    """Kiem tra cac file PDF/DOCX da co trong thu muc."""
    existing = []
    for path in sorted(DATA_DIR.iterdir()):
        if path.suffix.lower() in {".pdf", ".doc", ".docx"}:
            size_kb = path.stat().st_size / 1024
            if size_kb > 1:
                existing.append(path)
                print(f"  [EXISTS] {path.name} ({size_kb:.1f} KB)")
            else:
                print(f"  [WARN] {path.name} is too small ({size_kb:.1f} KB)")
    return existing


def download_document(filename: str, url: str, timeout: int = 30) -> bool:
    """Tai mot tai lieu tu URL cong khai."""
    output_path = DATA_DIR / filename

    if output_path.exists() and output_path.stat().st_size > 1024:
        print(f"  [SKIP] Already exists: {filename}")
        return True

    try:
        print(f"  Downloading: {filename} ...")
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (educational project)"},
        )
        response.raise_for_status()

        if len(response.content) < 1024:
            print(f"  [WARN] Downloaded file too small: {filename} ({len(response.content)} bytes)")
            return False

        output_path.write_bytes(response.content)
        print(f"  [OK] Saved: {filename} ({len(response.content) / 1024:.1f} KB)")
        return True

    except requests.exceptions.Timeout:
        print(f"  [FAIL] Timeout downloading: {filename}")
        return False
    except requests.exceptions.HTTPError as e:
        print(f"  [FAIL] HTTP error for {filename}: {e.response.status_code}")
        return False
    except Exception as e:
        print(f"  [FAIL] Error downloading {filename}: {e}")
        return False


def download_documents() -> None:
    """Kiem tra va tai tai lieu. Cac file da tai thu cong se duoc giu nguyen."""
    print("\n=== Kiem tra tai lieu da co ===")
    existing = check_existing_files()

    if len(existing) >= 3:
        print(f"\nDa co {len(existing)} tai lieu (>= 3 yeu cau). Khong can tai them.")
        return

    # Chi tai tu URL neu chua du 3 file
    print("\n=== Tai them tai lieu ===")
    for filename, url in DOWNLOADABLE_SOURCES.items():
        download_document(filename, url)

    # Kiem tra lai
    final_count = len([
        p for p in DATA_DIR.iterdir()
        if p.suffix.lower() in {".pdf", ".doc", ".docx"} and p.stat().st_size > 1024
    ])
    print(f"\nTong cong: {final_count} tai lieu hop le trong {DATA_DIR}")

    if final_count < 3:
        print("[WARN] Chua du 3 tai lieu! Hay tai them thu cong vao thu muc.")


if __name__ == "__main__":
    setup_directory()
    download_documents()
