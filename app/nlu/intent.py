import re
from typing import Dict, Any, Optional


def classify_intent(text: str) -> Dict[str, Any]:
    """Lightweight intent classifier returning intent, entities, and confidence.

    Returns:
      {"intent": str, "entities": {...}, "confidence": float, "clarify": Optional[str]}
    """
    t = text.lower().strip()
    if not t:
        return {"intent": "unknown", "entities": {}, "confidence": 0.0, "clarify": "Could you tell me what you want to do?"}

    # greetings
    if re.match(r'^(hi|hello|hey|hey there|hi there|good morning|good evening|good afternoon)\b', t):
        return {"intent": "greeting", "entities": {}, "confidence": 0.99}

    # add to cart / buy / purchase must win before generic cart-view checks
    if any(k in t for k in ("add ", "add to cart", "add to my cart", "buy ", "purchase ", "get me ", "put in cart", "put it in cart", "i want ")):
        entities = {}
        quantity_match = re.search(r"(\d+)\s*(?:x|pcs|pieces|items|qty|quantity)", t)
        if quantity_match:
            entities["quantity"] = int(quantity_match.group(1))

        product_id_match = re.search(r"(?:id|product)[:#\s]+(\d+)", t)
        if product_id_match:
            entities["product_id"] = int(product_id_match.group(1))

        name_match = re.search(r"(?:add|buy|get me|purchase|put|grab)(?: the| a| an)?\s+(.+?)(?: to cart| to my cart| for me| now|$)", t)
        if name_match:
            product_name = name_match.group(1).strip().rstrip(" ?")
            if product_name:
                entities["product_name"] = product_name

        return {"intent": "add_to_cart", "entities": entities, "confidence": 0.82, "clarify": None}

    # show cart: cart, basket, bag, order summary, items in my cart
    if (
        any(k in t for k in ("show my cart", "show cart", "view cart", "my cart", "cart", "basket", "bag", "what's in my cart", "what is in my cart", "items in my cart", "what is in my basket", "what's in my basket"))
        and not any(k in t for k in ("what are the items", "catalog", "list products", "add ", "buy ", "purchase "))
    ):
        return {"intent": "show_cart", "entities": {}, "confidence": 0.95}

    # show catalog
    if any(kw in t for kw in (
        "items available",
        "what are the items",
        "what items",
        "show catalog",
        "show me the catalog",
        "catalog",
        "list products",
        "available items",
        "what's available",
        "what do you sell",
        "products you have",
        "store items",
        "browse products",
        "look at the catalog",
    )):
        return {"intent": "show_catalog", "entities": {}, "confidence": 0.95}

    # checkout
    if any(kw in t for kw in ("checkout", "pay", "go ahead and checkout", "place order", "complete my purchase", "pay now")):
        return {"intent": "checkout", "entities": {}, "confidence": 0.95}

    # discount
    m_pct = re.search(r"(\d{1,2})\s*(?:%|percent|percentage)", t)
    if "discount" in t or m_pct or "offer" in t:
        entities = {}
        if m_pct:
            entities["discount_percent"] = int(m_pct.group(1))
        return {"intent": "apply_discount", "entities": entities, "confidence": 0.9}

    # search catalog
    if any(k in t for k in ("find ", "search ", "look for ", "looking for ", "find me ", "need ", "want " )):
        query = text.strip()
        return {"intent": "search_catalog", "entities": {"query": query}, "confidence": 0.8}

    # short natural queries often mean catalog search
    if len(t.split()) <= 6 and any(w in t for w in ("hoodie", "t-shirt", "shirt", "jeans", "sneaker", "beanie", "hat", "jacket", "product", "item")):
        return {"intent": "search_catalog", "entities": {"query": text}, "confidence": 0.75}

    # fallback
    return {"intent": "unknown", "entities": {}, "confidence": 0.4, "clarify": "Could you rephrase that or be more specific?"}
