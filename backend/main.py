from __future__ import annotations

import os
import re
import time
import asyncio
import html as html_lib
from typing import Any, Literal
from urllib.parse import urlparse

import httpx
import feedparser
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, HttpUrl

APP_VERSION = "0.6.1"
MAX_API = "https://platform-api2.max.ru"

def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()

app = FastAPI(title="MAX Publisher AI API", version=APP_VERSION, docs_url="/api/docs")

origins = [x.strip() for x in env("CORS_ORIGINS", "https://oraleeashe016-spec.github.io").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)

class SearchRequest(BaseModel):
    query: str = Field(default="", max_length=120)
    source: str = Field(default="all", max_length=40)
    min_discount: int = Field(default=0, ge=0, le=95)
    limit: int = Field(default=30, ge=1, le=100)

class DraftRequest(BaseModel):
    product_name: str = Field(min_length=1, max_length=300)
    current_price: str = Field(default="", max_length=40)
    previous_price: str = Field(default="", max_length=40)
    product_url: str = Field(default="", max_length=1000)
    facts: str = Field(default="", max_length=4000)
    tone: Literal["neutral", "energetic", "concise"] = "energetic"
    content_type: Literal["product", "rss"] = "product"
    source_name: str = Field(default="", max_length=120)
    published_at: str = Field(default="", max_length=80)

class PublishRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    confirmed: bool = False

SOURCES = {
    "yandex_market": ("Яндекс Маркет", "YANDEX_FEED_URL"),
    "ozon": ("Ozon", "OZON_FEED_URL"),
    "dns": ("DNS", "DNS_FEED_URL"),
    "mvideo": ("М.Видео", "MVIDEO_FEED_URL"),
    "citilink": ("Ситилинк", "CITILINK_FEED_URL"),
}

def require_api_key(value: str | None) -> None:
    expected = env("APP_API_KEY")
    if not expected:
        raise HTTPException(503, "APP_API_KEY is not configured on the backend")
    if not value or value != expected:
        raise HTTPException(401, "Invalid API key")

def configured_feed_url(key: str) -> str:
    url = env(SOURCES[key][1])
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise HTTPException(500, f"{key} feed must use HTTPS")
    return url

def source_status() -> list[dict[str, Any]]:
    return [
        {"id": key, "name": name, "configured": bool(configured_feed_url(key)), "mode": "json_feed" if configured_feed_url(key) else "not_configured"}
        for key, (name, _) in SOURCES.items()
    ]

def normalize_item(item: dict[str, Any], source_id: str) -> dict[str, Any] | None:
    try:
        name = str(item.get("name") or item.get("title") or "").strip()[:300]
        price = float(item.get("price"))
        old_price_raw = item.get("old_price")
        old_price = float(old_price_raw) if old_price_raw not in (None, "") else None
        if not name or price <= 0:
            return None
        discount = round((1 - price / old_price) * 100) if old_price and old_price > price else 0
        return {
            "id": str(item.get("id") or f"{source_id}:{name[:60]}"),
            "name": name,
            "source": source_id,
            "source_name": SOURCES[source_id][0],
            "price": round(price, 2),
            "old_price": round(old_price, 2) if old_price else None,
            "discount": max(0, min(95, discount)),
            "url": str(item.get("url") or ""),
            "image": str(item.get("image") or ""),
            "category": str(item.get("category") or "Техника"),
            "currency": str(item.get("currency") or "RUB"),
            "checked_at": str(item.get("checked_at") or ""),
            "is_demo": False,
        }
    except (TypeError, ValueError):
        return None

async def fetch_source(source_id: str, client: httpx.AsyncClient) -> list[dict[str, Any]]:
    url = configured_feed_url(source_id)
    if not url:
        return []
    response = await client.get(url, headers={"Accept": "application/json"})
    response.raise_for_status()
    payload = response.json()
    items = payload.get("items", []) if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        return []
    return [normalized for item in items if isinstance(item, dict) and (normalized := normalize_item(item, source_id))]

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": APP_VERSION, "timestamp": int(time.time())}

@app.get("/api/config")
async def config():
    return {
        "version": APP_VERSION,
        "sources": source_status(),
        "ai": {
            "mode": env("AI_MODE", "hybrid"),
            "cloud_provider": env("CLOUD_AI_PROVIDER", "groq").lower(),
            "cloud_model": env("CLOUD_AI_MODEL", "openai/gpt-oss-20b"),
            "ollama_configured": bool(env("OLLAMA_BASE_URL") and env("OLLAMA_MODEL")),
            "cloud_configured": bool(
                env("CLOUD_AI_API_KEY")
                and env("CLOUD_AI_MODEL", "openai/gpt-oss-20b")
                and env("CLOUD_AI_BASE_URL", "https://api.groq.com/openai/v1")
            ),
        },
        "max": {"configured": bool(env("MAX_BOT_TOKEN") and env("MAX_CHANNEL_ID"))},
    }

@app.post("/api/search")
async def search(request: SearchRequest):
    selected = list(SOURCES) if request.source == "all" else [request.source]
    if any(source not in SOURCES for source in selected):
        raise HTTPException(400, "Unknown source")
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    async with httpx.AsyncClient(timeout=12.0, follow_redirects=False) as client:
        for source_id in selected:
            try:
                results.extend(await fetch_source(source_id, client))
            except (httpx.HTTPError, ValueError) as exc:
                errors.append(f"{source_id}: feed unavailable ({type(exc).__name__})")
    query = request.query.casefold()
    results = [
        item for item in results
        if (not query or query in (item["name"] + " " + item["category"]).casefold())
        and item["discount"] >= request.min_discount
    ]
    results.sort(key=lambda item: item["discount"], reverse=True)
    return {"items": results[:request.limit], "count": len(results), "sources": source_status(), "errors": errors, "demo_data": False}


# Public editorial RSS feeds. These are news/review sources, not live store prices.
RSS_FEEDS = [
    {"id":"ixbt_news","name":"iXBT — Новости","url":"https://www.ixbt.com/export/news/rss.xml","category":"Новости техники","site":"iXBT"},
    {"id":"ixbt_articles","name":"iXBT — Статьи и обзоры","url":"https://www.ixbt.com/export/articles/rss.xml","category":"Обзоры","site":"iXBT"},
    {"id":"3dnews_hardware","name":"3DNews — Hardware","url":"https://3dnews.ru/news/rss/","category":"Компьютеры и железо","site":"3DNews"},
    {"id":"3dnews_software","name":"3DNews — Software","url":"https://3dnews.ru/software-news/rss/","category":"ПО и технологии","site":"3DNews"},
    {"id":"3dnews_mobile","name":"3DNews — Смартфоны","url":"https://3dnews.ru/phone/rss/","category":"Смартфоны","site":"3DNews"},
    {"id":"overclockers_news","name":"Overclockers — Новости","url":"https://overclockers.ru/rss/news.rss","category":"Комплектующие и ПК","site":"Overclockers.ru"},
    {"id":"overclockers_lab","name":"Overclockers — Обзоры","url":"https://overclockers.ru/rss/lab.rss","category":"Тесты и обзоры","site":"Overclockers.ru"},
]

def clean_rss_text(value: Any, limit: int = 900) -> str:
    raw = str(value or "")
    raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.I|re.S)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = html_lib.unescape(raw)
    return re.sub(r"\s+", " ", raw).strip()[:limit]

@app.get("/api/rss/feeds")
async def rss_feeds():
    return {"feeds": RSS_FEEDS, "count": len(RSS_FEEDS), "note": "RSS содержит редакционные материалы, а не подтверждённые цены магазинов."}

async def fetch_rss_feed(feed: dict[str, str], client: httpx.AsyncClient, query: str) -> tuple[list[dict[str, Any]], str | None]:
    try:
        # Stream with a hard byte cap and do not follow redirects. Feed URLs are a
        # fixed allowlist; refusing redirects prevents a feed host from redirecting
        # the backend toward an unrelated or private network address.
        body = bytearray()
        async with client.stream(
            "GET",
            feed["url"],
            headers={"Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"},
        ) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > 2_000_000:
                    return [], feed["id"] + ": feed too large"
        parsed = feedparser.parse(bytes(body))
        if parsed.bozo and not parsed.entries:
            return [], feed["id"] + ": invalid RSS"
        items: list[dict[str, Any]] = []
        for entry in parsed.entries[:40]:
            title = clean_rss_text(entry.get("title"), 300)
            link = str(entry.get("link") or "")
            if not title or not link.startswith(("https://", "http://")):
                continue
            summary = clean_rss_text(entry.get("summary") or entry.get("description") or "")
            published = str(entry.get("published") or entry.get("updated") or "")
            item = {
                "id": str(entry.get("id") or link),
                "title": title,
                "summary": summary,
                "url": link,
                "published": published,
                "source_id": feed["id"],
                "source_name": feed["name"],
                "category": feed["category"],
                "is_rss": True,
            }
            haystack = (title + " " + summary + " " + feed["category"]).casefold()
            if not query or query.casefold() in haystack:
                items.append(item)
        return items, None
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        return [], feed["id"] + ": feed unavailable"


@app.get("/api/rss/items")
async def rss_items(query: str = "", source: str = "all", limit: int = 40):
    if len(query) > 120 or not 1 <= limit <= 100:
        raise HTTPException(400, "Invalid query or limit")
    selected = [feed for feed in RSS_FEEDS if source == "all" or feed["id"] == source]
    if source != "all" and not selected:
        raise HTTPException(400, "Unknown RSS source")
    timeout = httpx.Timeout(12.0, connect=5.0)
    limits = httpx.Limits(max_connections=8, max_keepalive_connections=4)
    async with httpx.AsyncClient(timeout=timeout, limits=limits, follow_redirects=False, headers={"User-Agent": "MAX-Publisher-AI-Web/0.5.1 RSS reader"}) as client:
        results = await asyncio.gather(*(fetch_rss_feed(feed, client, query) for feed in selected))
    items = [item for feed_items, _ in results for item in feed_items]
    errors = [error for _, error in results if error]
    items.sort(key=lambda item: item["published"], reverse=True)
    return {"items": items[:limit], "count": len(items[:limit]), "feeds": RSS_FEEDS, "errors": errors, "is_rss": True}

def openai_compatible_payload(model: str, prompt: str) -> dict[str, Any]:
    return {"model": model, "messages": [
        {"role": "system", "content": "Ты редактор коротких товарных публикаций. Не выдумывай характеристики, наличие, скидки и условия. Используй только факты пользователя. Если данных нет — не утверждай их."},
        {"role": "user", "content": prompt},
    ], "temperature": 0.6}

async def call_chat_completion(base_url: str, model: str, api_key: str, prompt: str) -> str:
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    async with httpx.AsyncClient(timeout=35.0) as client:
        response = await client.post(url, headers=headers, json=openai_compatible_payload(model, prompt))
        response.raise_for_status()
        data = response.json()
    return str(data["choices"][0]["message"]["content"]).strip()

def build_ai_prompt(request: DraftRequest) -> str:
    if request.content_type == "rss":
        return (
            "Переработай предоставленную RSS-новость в самостоятельный короткий пост для канала MAX. "
            "Не выдавай пересказ за оригинальный репортаж и не добавляй сведения, которых нет во входных данных. "
            "Сохрани точные имена, модели, числа и смысл. Не придумывай цены, скидки, наличие, цитаты или характеристики. "
            "Не делай категоричных выводов сверх источника. Используй нейтральный новостной стиль. "
            "Не копируй длинные фрагменты исходного текста; сделай краткое изложение своими словами. "
            "В конце отдельной строкой укажи источник и ссылку, если они предоставлены. "
            "Верни только готовый текст поста, без пояснений редактора.\n\n"
            f"Заголовок: {request.product_name}\n"
            f"Источник: {request.source_name or 'не указан'}\n"
            f"Дата публикации: {request.published_at or 'не указана'}\n"
            f"Ссылка на оригинал: {request.product_url or 'не указана'}\n"
            f"Текст/описание RSS: {request.facts or 'описание отсутствует'}\n"
            f"Формат: {request.tone}\n"
        )
    return (
        f"Подготовь пост для канала MAX в стиле {request.tone}.\n"
        f"Товар: {request.product_name}\nТекущая цена: {request.current_price or 'не указана'}\n"
        f"Предыдущая цена: {request.previous_price or 'не указана'}\n"
        f"Ссылка: {request.product_url or 'не указана'}\nФакты: {request.facts or 'не указаны'}\n"
        "Не называй предложение скидкой, если подтверждающей цены нет. Не добавляй неподтверждённые факты."
    )


@app.post("/api/ai/draft")
async def ai_draft(request: DraftRequest, x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    prompt = build_ai_prompt(request)
    mode = env("AI_MODE", "hybrid").lower()
    ollama_url, ollama_model = env("OLLAMA_BASE_URL"), env("OLLAMA_MODEL")
    cloud_provider = env("CLOUD_AI_PROVIDER", "groq").lower()
    cloud_url = env("CLOUD_AI_BASE_URL", "https://api.groq.com/openai/v1")
    cloud_key = env("CLOUD_AI_API_KEY")
    cloud_model = env("CLOUD_AI_MODEL", "openai/gpt-oss-20b")
    if mode in ("hybrid", "ollama") and ollama_url and ollama_model:
        try:
            text = await call_chat_completion(ollama_url, ollama_model, "", prompt)
            return {"text": text, "provider": "ollama", "model": ollama_model}
        except (httpx.HTTPError, KeyError, IndexError, ValueError):
            if mode == "ollama":
                raise HTTPException(502, "Ollama provider unavailable")
    if mode in ("hybrid", "cloud") and cloud_url and cloud_key and cloud_model:
        try:
            text = await call_chat_completion(cloud_url, cloud_model, cloud_key, prompt)
            return {"text": text, "provider": cloud_provider, "model": cloud_model}
        except httpx.HTTPStatusError as exc:
            if exc.response is not None and exc.response.status_code == 429:
                raise HTTPException(429, "AI quota reached. Wait for the provider limit reset.")
            raise HTTPException(502, "Cloud AI provider rejected the request")
        except (httpx.HTTPError, KeyError, IndexError, ValueError):
            raise HTTPException(502, "Cloud AI provider unavailable")
    raise HTTPException(503, "No AI provider is configured")

@app.post("/api/max/publish")
async def max_publish(request: PublishRequest, x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    if not request.confirmed:
        raise HTTPException(400, "Explicit confirmation is required")
    token, channel_id = env("MAX_BOT_TOKEN"), env("MAX_CHANNEL_ID")
    if not token or not channel_id:
        raise HTTPException(503, "MAX_BOT_TOKEN and MAX_CHANNEL_ID must be configured on the backend")
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            f"{MAX_API}/messages",
            params={"chat_id": channel_id},
            headers={"Authorization": token, "Content-Type": "application/json"},
            json={"text": request.text, "format": "markdown"},
        )
    if response.status_code >= 400:
        raise HTTPException(response.status_code, "MAX API rejected the publication")
    result = response.json()
    if isinstance(result, dict) and result.get("success") is False:
        raise HTTPException(502, "MAX API reported unsuccessful publication")
    return {"sent": True, "result": result}
