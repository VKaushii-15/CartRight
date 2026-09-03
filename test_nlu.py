from app.nlu.intent import classify_intent


def test_show_cart_variants():
    assert classify_intent("show me my cart")["intent"] == "show_cart"
    assert classify_intent("what's in my basket")["intent"] == "show_cart"
    assert classify_intent("view cart contents")["intent"] == "show_cart"


def test_show_catalog_variants():
    assert classify_intent("what are the items available in the store")["intent"] == "show_catalog"
    assert classify_intent("show me the catalog")["intent"] == "show_catalog"
    assert classify_intent("what do you sell")["intent"] == "show_catalog"


def test_search_and_add_intents():
    assert classify_intent("find a red hoodie")["intent"] == "search_catalog"
    assert classify_intent("add blue hoodie to cart")["intent"] == "add_to_cart"
    assert classify_intent("buy 2 black jeans")["intent"] == "add_to_cart"


def test_discount_intent():
    result = classify_intent("give me a 15 percent discount")
    assert result["intent"] == "apply_discount"
    assert result["entities"]["discount_percent"] == 15
