"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown.

Hướng dẫn:
    1. Dùng MarkItDown để convert PDF/DOCX.
    2. Đọc JSON và giữ metadata ở đầu file Markdown.
    3. Giữ cấu trúc thư mục legal/ và news/.
    4. Không tạo file rỗng hoặc file trùng khi chạy lại.

Cài đặt:
    Dependency MarkItDown đã được khai báo trong pyproject.toml.
    
-> Hoặc dùng công cụ nào bạn quen khác Markitdown
"""

import json
import sys
from pathlib import Path

# Fix Windows cp1252 console encoding for Vietnamese filenames
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from markitdown import MarkItDown


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def convert_legal_docs() -> None:
    """Convert PDF/DOCX from landing/legal/ to standardized/legal/ as Markdown."""
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    converter = MarkItDown()
    converted = 0
    skipped = 0

    for path in sorted(legal_dir.iterdir()):
        if path.suffix.lower() not in {".pdf", ".doc", ".docx"}:
            continue

        output_path = output_dir / f"{path.stem}.md"

        # Skip if already converted and source hasn't changed
        if output_path.exists() and output_path.stat().st_mtime > path.stat().st_mtime:
            print(f"  [SKIP] Already converted: {path.name}")
            skipped += 1
            continue

        try:
            print(f"  Converting: {path.name} ...")
            result = converter.convert(str(path))

            if not result.text_content or not result.text_content.strip():
                print(f"  [WARN] Empty content from: {path.name}")
                continue

            # Add metadata header
            header = (
                f"# {path.stem}\n\n"
                f"**Source file:** {path.name}\n\n"
                f"**Type:** {path.suffix.upper().lstrip('.')}\n\n---\n\n"
            )
            output_path.write_text(header + result.text_content, encoding="utf-8")
            print(f"  [OK] Saved: {output_path.name} ({len(result.text_content)} chars)")
            converted += 1
        except Exception as e:
            print(f"  [FAIL] {path.name} -- {e}")

    print(f"  Legal docs: {converted} converted, {skipped} skipped")


def convert_news_articles() -> None:
    """Convert JSON articles from landing/news/ to standardized/news/ as Markdown."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    converted = 0
    skipped = 0

    for path in sorted(news_dir.glob("*.json")):
        output_path = output_dir / f"{path.stem}.md"

        # Skip if already converted and source hasn't changed
        if output_path.exists() and output_path.stat().st_mtime > path.stat().st_mtime:
            print(f"  [SKIP] Already converted: {path.name}")
            skipped += 1
            continue

        try:
            data = json.loads(path.read_text(encoding="utf-8"))

            content = data.get("content_markdown", "").strip()
            if not content:
                print(f"  [WARN] Empty content in: {path.name}")
                continue

            header = (
                f"# {data.get('title', 'Untitled')}\n\n"
                f"**Source:** {data.get('url', 'N/A')}\n\n"
                f"**Crawled:** {data.get('date_crawled', 'N/A')}\n\n---\n\n"
            )
            output_path.write_text(header + content, encoding="utf-8")
            print(f"  [OK] Saved: {output_path.name} ({len(content)} chars)")
            converted += 1
        except Exception as e:
            print(f"  [FAIL] {path.name} -- {e}")

    print(f"  News articles: {converted} converted, {skipped} skipped")


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=== Converting legal documents ===")
    convert_legal_docs()

    print("\n=== Converting news articles ===")
    convert_news_articles()

    print(f"\nDone! Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
