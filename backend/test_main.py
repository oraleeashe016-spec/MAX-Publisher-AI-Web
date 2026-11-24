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
    assert response.json()["version"] == "0.5.0"


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
