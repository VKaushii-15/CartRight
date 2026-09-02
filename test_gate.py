#!/usr/bin/env python3
"""
Test suite for Phase 2 gate layer.
Hand-crafted tool call tests (no LLM involved).
Verifies: schema validation, business rule enforcement, graceful error handling.
"""

import sys
from sqlalchemy.orm import Session

from app.db import SessionLocal, engine, Base
from app.models import Product, Cart, Order
from app.tools import run_tool_call
from app.tools.schemas import ToolCallResult


def setup_test_db():
    """Create fresh test database and seed with products."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Seed test products
    products = [
        Product(id=1, name="Blue Hoodie", description="Comfortable blue hoodie", price=1500.0, stock=10),
        Product(id=2, name="Red T-Shirt", description="Classic red t-shirt", price=500.0, stock=5),
        Product(id=3, name="Black Jeans", description="Slim fit black jeans", price=2500.0, stock=3),
    ]
    for p in products:
        db.add(p)
    db.commit()
    db.close()


def test_case(name: str, tool_name: str, arguments: dict, session_id: str = "test_session") -> ToolCallResult:
    """Execute a test case and return result."""
    db = SessionLocal()
    result = run_tool_call(tool_name, arguments, session_id, db)
    db.close()
    return result


def assert_ok(result: ToolCallResult, test_name: str):
    """Assert result status is 'ok'."""
    if result.status != "ok":
        print(f"❌ {test_name}: Expected status='ok', got '{result.status}'")
        print(f"   Message: {result.message}")
        return False
    print(f"✅ {test_name}")
    return True


def assert_rejected(result: ToolCallResult, test_name: str):
    """Assert result status is 'rejected'."""
    if result.status != "rejected":
        print(f"❌ {test_name}: Expected status='rejected', got '{result.status}'")
        return False
    print(f"✅ {test_name}: Correctly rejected with message: {result.message}")
    return True


def run_all_tests():
    """Execute all test cases."""
    print("\n" + "="*70)
    print("PHASE 2 GATE LAYER TEST SUITE")
    print("="*70 + "\n")
    
    setup_test_db()
    passed = 0
    failed = 0
    
    # ========== SEARCH CATALOG TESTS ==========
    print("--- SEARCH CATALOG ---")
    
    result = test_case(
        "Search catalog: 'Blue' query",
        "search_catalog",
        {"query": "Blue", "limit": 5}
    )
    if assert_ok(result, "Search catalog: valid query"):
        data = result.data
        if data["count"] == 1 and data["results"][0]["name"] == "Blue Hoodie":
            print(f"   Result: Found {data['count']} product(s)")
            passed += 1
        else:
            print(f"   ❌ Unexpected search results")
            failed += 1
    else:
        failed += 1
    
    result = test_case(
        "Search catalog: no matches",
        "search_catalog",
        {"query": "Nonexistent", "limit": 5}
    )
    if assert_ok(result, "Search catalog: empty results"):
        data = result.data
        if data["count"] == 0:
            print(f"   Result: Found {data['count']} product(s)")
            passed += 1
        else:
            print(f"   ❌ Expected 0 results, got {data['count']}")
            failed += 1
    else:
        failed += 1
    
    # ========== ADD TO CART TESTS ==========
    print("\n--- ADD TO CART ---")
    
    result = test_case(
        "Add to cart: valid product",
        "add_to_cart",
        {"product_id": 1, "quantity": 2},
        session_id="session_1"
    )
    if assert_ok(result, "Add to cart: product 1, qty 2"):
        data = result.data
        print(f"   Cart total: ₹{data['cart_total']}, Items: {data['cart_item_count']}")
        passed += 1
    else:
        failed += 1
    
    result = test_case(
        "Add to cart: nonexistent product",
        "add_to_cart",
        {"product_id": 999, "quantity": 1},
        session_id="session_1"
    )
    if assert_rejected(result, "Add to cart: nonexistent product"):
        passed += 1
    else:
        failed += 1
    
    result = test_case(
        "Add to cart: insufficient stock",
        "add_to_cart",
        {"product_id": 3, "quantity": 100},  # Only 3 in stock
        session_id="session_1"
    )
    if assert_rejected(result, "Add to cart: insufficient stock"):
        passed += 1
    else:
        failed += 1
    
    # Add more items for discount/checkout tests
    test_case("Pre-test: Add item 2", "add_to_cart", {"product_id": 2, "quantity": 1}, "session_1")
    
    # ========== APPLY DISCOUNT TESTS ==========
    print("\n--- APPLY DISCOUNT ---")
    
    result = test_case(
        "Apply discount: 15%",
        "apply_discount",
        {"discount_percent": 15},
        session_id="session_1"
    )
    if assert_ok(result, "Apply discount: 15% (valid)"):
        data = result.data
        print(f"   Subtotal: ₹{data['cart_subtotal']}, Discount: ₹{data['discount_amount']}, Total: ₹{data['cart_total']}")
        passed += 1
    else:
        failed += 1
    
    result = test_case(
        "Apply discount: 20% (max allowed)",
        "apply_discount",
        {"discount_percent": 20},
        session_id="session_1"
    )
    if assert_ok(result, "Apply discount: 20% (at max cap)"):
        passed += 1
    else:
        failed += 1
    
    result = test_case(
        "Apply discount: 25% (over limit)",
        "apply_discount",
        {"discount_percent": 25},
        session_id="session_1"
    )
    if assert_rejected(result, "Apply discount: 25% (gated by schema validation)"):
        passed += 1
    else:
        failed += 1
    
    result = test_case(
        "Apply discount: -5% (invalid)",
        "apply_discount",
        {"discount_percent": -5},
        session_id="session_1"
    )
    if assert_rejected(result, "Apply discount: -5% (negative not allowed)"):
        passed += 1
    else:
        failed += 1
    
    # ========== CHECKOUT TESTS ==========
    print("\n--- CHECKOUT ---")
    
    result = test_case(
        "Checkout: cart with items and discount",
        "checkout",
        {},  # No arguments
        session_id="session_1"
    )
    if assert_ok(result, "Checkout: valid cart"):
        data = result.data
        print(f"   Razorpay Order ID: {data['razorpay_order_id']}")
        print(f"   Amount: ₹{data['amount']}, Currency: {data['currency']}")
        passed += 1
    else:
        failed += 1
    
    result = test_case(
        "Checkout: empty cart",
        "checkout",
        {},
        session_id="session_empty"
    )
    if assert_rejected(result, "Checkout: empty cart (rejected)"):
        passed += 1
    else:
        failed += 1
    
    # ========== UPSELL SUGGEST TESTS ==========
    print("\n--- UPSELL SUGGEST ---")
    
    result = test_case(
        "Upsell: suggest related products",
        "upsell_suggest",
        {},
        session_id="session_1"
    )
    if assert_ok(result, "Upsell: suggestion engine"):
        data = result.data
        print(f"   Suggestions: {len(data['suggestions'])} product(s)")
        for sugg in data['suggestions']:
            print(f"     - {sugg['name']}: {sugg['reason']}")
        passed += 1
    else:
        failed += 1
    
    # ========== UNKNOWN TOOL TESTS ==========
    print("\n--- UNKNOWN TOOL ---")
    
    result = test_case(
        "Unknown tool: 'invalid_tool'",
        "invalid_tool",
        {},
        session_id="session_1"
    )
    if assert_rejected(result, "Unknown tool (whitelist rejection)"):
        passed += 1
    else:
        failed += 1
    
    # ========== MALFORMED ARGUMENT TESTS ==========
    print("\n--- MALFORMED ARGUMENTS ---")
    
    result = test_case(
        "Search catalog: missing 'query' argument",
        "search_catalog",
        {"limit": 5},  # Missing required 'query'
        session_id="session_1"
    )
    if assert_rejected(result, "Search catalog: missing required argument"):
        passed += 1
    else:
        failed += 1
    
    result = test_case(
        "Add to cart: wrong type for quantity",
        "add_to_cart",
        {"product_id": 1, "quantity": "invalid"},  # Should be int
        session_id="session_1"
    )
    if assert_rejected(result, "Add to cart: type validation (quantity)"):
        passed += 1
    else:
        failed += 1
    
    # ========== SUMMARY ==========
    print("\n" + "="*70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*70 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
