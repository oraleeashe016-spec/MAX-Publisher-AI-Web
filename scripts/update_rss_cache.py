#!/usr/bin/env python3
"""Build a static, same-origin RSS cache for GitHub Pages."""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import html
import json
import re
import urllib.request
from email.utils import parsedate_to_datetime
from pathlib import Path

import feedparser

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "rss-feed.json"
MAX_BYTES = 2_000_000
FEEDS = [
    {"id": "ixbt_news", "name": "iXBT — Новости", "url": "https://www.ixbt.com/export/news/rss.xml", "category": "Новости техники"},
    {"id": "ixbt_articles", "name": "iXBT — Статьи и обзоры", "url": "https://www.ixbt.com/export/articles/rss.xml", "category": "Обзоры"},
    {"id": "3dnews_hardware", "name": "3DNews — Hardware", "url": "https://3dnews.ru/news/rss/", "category": "Компьютеры и железо"},
    {"id": "3dnews_software", "name": "3DNews — Software", "url": "https://3dnews.ru/software-news/rss/", "category": "ПО и технологии"},
    {"id": "3dnews_mobile", "name": "3DNews — Смартфоны", "url": "https://3dnews.ru/phone/rss/", "category": "Смартфоны"},
    {"id": "overclockers_news", "name": "Overclockers — Новости", "url": "https://overclockers.ru/rss/news.rss", "category": "Комплектующие и ПК"},
    {"id": "overclockers_lab", "name": "Overclockers — Обзоры", "url": "https://overclockers.ru/rss/lab.rss", "category": "Тесты и обзоры"},
]


def clean(value: object, limit: int = 900) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", str(value or ""), flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()[:limit]


def published(entry: dict) -> str:
    raw = entry.get("published") or entry.get("updated") or ""
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        try:
            return dt.datetime(*parsed[:6], tzinfo=dt.timezone.utc).isoformat()
        except (TypeError, ValueError):
            pass
    if raw:
        try:
            value = parsedate_to_datetime(raw)
            if value.tzinfo is None:
                value = value.replace(tzinfo=dt.timezone.utc)
            return value.astimezone(dt.timezone.utc).isoformat()
        except (TypeError, ValueError, OverflowError):
            return clean(raw, 80)
    return ""


def fetch_feed(feed: dict) -> tuple[str, list[dict], str | None]:
    request = urllib.request.Request(
        feed["url"],
        headers={"User-Agent": "MAX-Publisher-AI-RSS/0.5.3 (+GitHub Pages)", "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError("feed exceeds 2 MB")
        parsed = feedparser.parse(body)
        if parsed.bozo and not parsed.entries:
            raise ValueError("invalid RSS/Atom document")
        items = []
        for entry in parsed.entries[:60]:
            title = clean(entry.get("title"), 300)
            link = str(entry.get("link") or "").strip()
            if not title or not link.startswith("https://"):
                continue
            items.append({
                "id": str(entry.get("id") or link)[:500],
                "title": title,
                "summary": clean(entry.get("summary") or entry.get("description"), 900),
                "url": link[:1500],
                "published": published(entry),
                "source_id": feed["id"],
                "source_name": feed["name"],
                "category": feed["category"],
            })
        return feed["id"], items, None
    except Exception as exc:
        return feed["id"], [], f"{type(exc).__name__}: {str(exc)[:180]}"


def main() -> None:
    previous = {}
    if OUTPUT.exists():
        try:
            previous = json.loads(OUTPUT.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous = {}
    old_by_source: dict[str, list[dict]] = {}
    for item in previous.get("items", []):
        old_by_source.setdefault(item.get("source_id", ""), []).append(item)

    collected: dict[str, list[dict]] = {}
    errors = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:
        results = list(pool.map(fetch_feed, FEEDS))
    feed_status = []
    for source_id, items, error in results:
        if error:
            errors.append({"source_id": source_id, "error": error})
            items = old_by_source.get(source_id, [])
        collected[source_id] = items
        feed_status.append({"id": source_id, "count": len(items), "updated": not bool(error), "error": error})

    all_items = []
    seen = set()
    for feed in FEEDS:
        for item in collected.get(feed["id"], []):
            key = item.get("url") or item.get("id")
            if key in seen:
                continue
            seen.add(key)
            all_items.append(item)
    all_items.sort(key=lambda item: item.get("published", ""), reverse=True)
    payload = {
        "version": "0.5.3",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "count": len(all_items),
        "feeds": feed_status,
        "errors": errors,
        "items": all_items[:300],
        "note": "RSS содержит редакционные материалы, а не подтверждённые цены или скидки магазинов.",
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"RSS cache generated: {len(all_items)} items; {len(errors)} feed errors")
    for status in feed_status:
        print(f"- {status['id']}: {status['count']} items; updated={status['updated']}")


if __name__ == "__main__":
    main()
