from main import normalize_item

def test_normalize_item_calculates_discount_from_reference_price():
    item = normalize_item(
        {"id": "sku-1", "name": "Test phone", "price": 7500, "old_price": 10000, "url": "https://shop.example/item"},
        "dns",
    )
    assert item is not None
    assert item["discount"] == 25
    assert item["price"] == 7500
    assert item["is_demo"] is False

def test_normalize_item_does_not_claim_discount_without_higher_old_price():
    item = normalize_item({"name": "Test item", "price": 1000, "old_price": 900}, "ozon")
    assert item is not None
    assert item["discount"] == 0

def test_normalize_item_rejects_invalid_price():
    assert normalize_item({"name": "Broken", "price": "unknown"}, "citilink") is None


from fastapi.testclient import TestClient
import main

client = TestClient(main.app)


def test_health_reports_current_backend_version():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["version"] == "0.5.1"


def test_rss_feed_directory_is_fixed_and_https_only():
    response = client.get("/api/rss/feeds")
    payload = response.json()
    assert response.status_code == 200
    assert payload["count"] == 7
    assert len({feed["id"] for feed in payload["feeds"]}) == 7
    assert all(feed["url"].startswith("https://") for feed in payload["feeds"])


def test_rss_items_reject_unknown_feed():
    response = client.get("/api/rss/items", params={"source": "unknown-feed"})
    assert response.status_code == 400


def test_rss_items_reject_invalid_limit():
    response = client.get("/api/rss/items", params={"limit": 101})
    assert response.status_code == 400


def test_clean_rss_text_removes_markup_and_unescapes_entities():
    assert main.clean_rss_text("<p>Hello &amp; <b>world</b></p>") == "Hello & world"


def test_config_does_not_expose_backend_secrets():
    response = client.get("/api/config")
    assert response.status_code == 200
    for secret_name in ("APP_API_KEY", "MAX_BOT_TOKEN", "CLOUD_AI_API_KEY"):
        assert secret_name not in response.text


import asyncio


class FakeRSSResponse:
    def __init__(self, body: bytes, status_code: int = 200):
        self.body = body
        self.status_code = status_code

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError("bad response", request=None, response=None)

    async def aiter_bytes(self):
        for offset in range(0, len(self.body), 64):
            yield self.body[offset:offset + 64]


class FakeRSSClient:
    def __init__(self, body: bytes):
        self.body = body
        self.requested_url = None

    def stream(self, method, url, headers=None):
        self.requested_url = url
        return FakeRSSResponse(self.body)


def test_fetch_rss_feed_parses_entry_and_filters_query():
    xml = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>Test</title>
    <item><title>New smartphone review</title><link>https://example.com/review</link>
    <description>Review of a new phone</description><pubDate>Tue, 24 Nov 2026 10:00:00 GMT</pubDate></item>
    </channel></rss>"""
    client = FakeRSSClient(xml)
    items, error = asyncio.run(main.fetch_rss_feed(main.RSS_FEEDS[0], client, "smartphone"))
    assert error is None
    assert len(items) == 1
    assert items[0]["title"] == "New smartphone review"
    assert items[0]["is_rss"] is True


def test_fetch_rss_feed_rejects_unrelated_query():
    xml = b"""<?xml version="1.0"?><rss version="2.0"><channel>
    <item><title>Weather report</title><link>https://example.com/weather</link></item>
    </channel></rss>"""
    items, error = asyncio.run(main.fetch_rss_feed(main.RSS_FEEDS[0], FakeRSSClient(xml), "smartphone"))
    assert items == []
    assert error is None


def test_fetch_rss_feed_rejects_oversized_payload():
    items, error = asyncio.run(main.fetch_rss_feed(main.RSS_FEEDS[0], FakeRSSClient(b"x" * 2_000_001), ""))
    assert items == []
    assert error and "too large" in error
