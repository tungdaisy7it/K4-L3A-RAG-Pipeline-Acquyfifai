"""
Task 2 — Crawl bài viết/thông báo.

Hướng dẫn:
    1. Điền tối thiểu 5 URL công khai vào ARTICLE_URLS.
    2. Crawl từng URL bằng Crawl4AI.
    3. Lưu mỗi bài thành một JSON trong data/landing/news/.
    4. Giữ đủ url, title, date_crawled và content_markdown.

Cài browser trước khi chạy:
    python -m playwright install chromium

-> Dùng Firecrawl or bất cứ công cụ nào bạn quen    
"""

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

ARTICLE_URLS = [
    # --- Danang Fantasticity (English) ---
    "https://danangfantasticity.com/en/son-tra-peninsula",
    "https://danangfantasticity.com/en/culture-en/marble-mountains",
    "https://danangfantasticity.com/en/discovery/my-khe-beach-one-of-the-ten-most-beautiful-beaches-in-asia",
    "https://danangfantasticity.com/en/dragon-bridge",
    "https://danangfantasticity.com/en/linh-ung-pagoda",
    "https://danangfantasticity.com/en/overview-da-nang-museum-of-cham-sculpture",
    "https://danangfantasticity.com/en/see-and-do/my-son-sanctuary",
    "https://danangfantasticity.com/en/tag/hai-van-pass",
    "https://danangfantasticity.com/en/summer-2026-open-the-gates-to-ba-na-and-discover-four-magical-worlds",
    "https://danangfantasticity.com/en/discovery/explore-ba-na-hills-during-the-april-30-may-1-holiday",
    "https://danangfantasticity.com/en/touch-tet-moments-by-the-han-river-dragon-bridge-and-the-springtime-river-show-2026",
    "https://danangfantasticity.com/en/best-beaches-da-nang",
    "https://danangfantasticity.com/en/explore-the-natural-beauty-of-da-nang",
    "https://danangfantasticity.com/en/discovery/discover-my-son-with-ease-ticket-prices-distance-transportation-useful-travel-tips",
    "https://danangfantasticity.com/en/news/new-tourism-products-in-da-nang-2026",
    # --- Danang Fantasticity (Vietnamese / Chinese) ---
    "https://danangfantasticity.com/en/kham-pha/danh-thang-ngu-hanh-son-da-nang",
    "https://danangfantasticity.com/cn/danh-thang-ngu-hanh-son-goi-y-lich-trinh-tham-quan",
    "https://danangfantasticity.com/tin-tuc/su-hinh-thanh-va-mot-vai-dien-co-lich-su-ve-ngu-hanh-son.html",
    "https://danangfantasticity.com/kinh-nghiem-du-lich-da-nang-tu-tuc",
    # --- External travel sites ---
    "https://vinpearl.com/vi/tat-tan-tat-tu-a-z-cam-nang-du-lich-da-nang-tu-tuc",
    "https://www.traveloka.com/vi-vn/explore/destination/du-lich-da-nang-3-ngay-2-dem/145822",
    "https://www.ivivu.com/blog/2025/04/tat-tan-tat-kinh-nghiem-du-lich-da-nang-2025/",
    "https://mia.vn/cam-nang-du-lich/du-lich-da-nang-12050",
    "https://tourism.danang.vn/gioi-thieu-thanh-pho-da-nang/",
    # --- Food & cuisine ---
    "https://danangfantasticity.com/tinh-hoa-am-thuc-da-nang/mi-quang",
    "https://danangfantasticity.com/en/am-thuc-dia-phuong/banh-trang-cuon-thit-heo",
    "https://danangfantasticity.com/en/kham-pha/thuong-thuc-cac-mon-soi-noi-tieng-o-da-nang",
    "https://danangfantasticity.com/en/lac-buoc-giua-thien-duong-am-thuc-duong-pho-da-nang",
    "https://danangfantasticity.com/en/tri-thuc-dan-gian/tri-thuc-dan-gian-mi-quang",
    "https://danangfantasticity.com/cn/kham-pha/da-nang-phat-trien-am-thuc-thanh-san-pham-du-lich-dac-sac",
    "https://danangfantasticity.com/en/an-uong/am-thuc-dia-phuong-trong-khong-gian-nghi-duong-sang-trong-tai-da-nang",
    # --- Events, culture, tourism policy ---
    "https://danangfantasticity.com/vi/kham-pha/diem-danh-cac-san-pham-du-lich-moi-tai-da-nang-2026",
    "https://danangfantasticity.com/en/danh-hieu-du-lich-da-nang-2026",
    "https://danangfantasticity.com/vi/category/bao-tang-lich-su-va-van-hoa?id=12899",
    "https://danangfantasticity.com/vi/kham-pha/le-hoi-su-kien-da-nang-6-thang-cuoi-nam-2026",
    # --- Government sources ---
    "https://danang.gov.vn/w/trien-khai-ke-hoach-phat-trien-du-lich-da-nang-nam-2025-i",
    "https://danang.gov.vn/w/dinh-huong-phat-trien-du-lich-da-nang-theo-huong-ben-vung-hai-hoa-voi-thien-nhien-va-moi-truong-i",
    "https://danang.gov.vn/w/ban-hanh-bo-tieu-chi-van-hoa-du-lich-da-nang-i",
    "https://danang.gov.vn/w/phat-trien-du-lich-hien-dai-chat-luong-cao-huong-den-tang-truong-ben-vung",
]


def _slugify(url: str) -> str:
    """Create a short, filesystem-safe slug from a URL."""
    # Take the path portion, strip leading/trailing slashes
    path = url.split("//", 1)[-1].split("/", 1)[-1].strip("/")
    # Replace non-alphanum with hyphens, collapse multiples
    slug = re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-")
    # Truncate to a reasonable length
    return slug[:80] if slug else "index"


async def crawl_article(crawler: AsyncWebCrawler, url: str) -> dict:
    """Crawl a single URL and return the article dict."""
    run_config = CrawlerRunConfig(
        word_count_threshold=10,
        page_timeout=60000,
        wait_until="domcontentloaded",
    )

    result = await crawler.arun(url=url, config=run_config)

    if not result.success:
        raise RuntimeError(f"Crawl failed: {result.error_message}")

    title = "Unknown"
    if result.metadata and isinstance(result.metadata, dict):
        title = result.metadata.get("title", "Unknown")

    content = result.markdown or ""
    if not content.strip():
        content = result.cleaned_html or ""

    return {
        "url": url,
        "title": title,
        "date_crawled": datetime.now(timezone.utc).isoformat(),
        "content_markdown": content,
    }


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    browser_config = BrowserConfig(
        headless=True,
        browser_type="chromium",
    )

    success_count = 0
    fail_count = 0

    async with AsyncWebCrawler(config=browser_config) as crawler:
        for index, url in enumerate(ARTICLE_URLS, 1):
            slug = _slugify(url)
            output = DATA_DIR / f"article_{index:02d}_{slug}.json"
            try:
                print(f"[{index}/{len(ARTICLE_URLS)}] Crawling: {url}")
                article = await crawl_article(crawler, url)

                # Skip articles with very little content
                if len(article["content_markdown"].strip()) < 50:
                    print(f"  [SKIP] Too little content: {url}")
                    fail_count += 1
                    continue

                output.write_text(
                    json.dumps(article, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                print(f"  [OK] Saved: {output.name} "
                      f"({len(article['content_markdown'])} chars)")
                success_count += 1

                # Small delay to be polite to servers
                await asyncio.sleep(1.5)

            except Exception as error:
                print(f"  [FAIL] {url} -- {error}")
                fail_count += 1

    print(f"\n{'='*60}")
    print(f"Done! {success_count} succeeded, {fail_count} failed "
          f"out of {len(ARTICLE_URLS)} URLs.")
    print(f"Files saved to: {DATA_DIR}")


if __name__ == "__main__":
    asyncio.run(crawl_all())
