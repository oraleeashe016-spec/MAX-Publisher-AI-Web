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
