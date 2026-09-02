#!/usr/bin/env python3
"""
DEMO SCRIPT: Full end-to-end conversational checkout flow.
Shows complete pipeline: REST API → Tool calls → Gate validation → Database → Razorpay

This script demonstrates:
1. Catalog search
2. Add to cart
3. Apply discount (with gating)
4. Checkout (real Razorpay order)
5. Graceful rejection (attempting invalid discount)
"""

import requests
import json

# ============================================================================
# Configuration
# ============================================================================

BASE_URL = "http://localhost:8000"
SESSION_ID = "demo_session_001"

print("\n" + "="*70)
print("CONVERSATIONAL CHECKOUT AGENT — FULL DEMO")
print("="*70 + "\n")

# ============================================================================
# Demo Flow
# ============================================================================

print("📍 Session ID:", SESSION_ID)
print("\n--- STEP 1: SEARCH CATALOG ---")
print("User: Looking for a blue hoodie\n")

response = requests.post(
    f"{BASE_URL}/tools/call?session_id={SESSION_ID}",
    json={
        "tool_name": "search_catalog",
        "arguments": {"query": "blue hoodie", "limit": 5}
    }
)
result = response.json()
print(f"Status: {result['status']}")
if result.get('data'):
    products = result['data'].get('results', [])
    for p in products[:2]:
        print(f"  ✓ {p['name']} — ₹{p['price']} (Stock: {p['stock']})")

# ============================================================================

print("\n--- STEP 2: ADD TO CART ---")
print("User: Add the blue hoodie (product ID 1), quantity 1\n")

response = requests.post(
    f"{BASE_URL}/tools/call?session_id={SESSION_ID}",
    json={
        "tool_name": "add_to_cart",
        "arguments": {"product_id": 1, "quantity": 1}
    }
)
result = response.json()
print(f"Status: {result['status']}")
if result['status'] == 'ok':
    data = result.get('data', {})
    print(f"  ✓ Added to cart")
    print(f"    Cart total: ₹{data.get('cart_total', 0)}")
    print(f"    Items in cart: {data.get('cart_item_count', 0)}")

# ============================================================================

print("\n--- STEP 3: ATTEMPT INVALID DISCOUNT (Test Gating) ---")
print("User: Apply a 25% discount\n")

response = requests.post(
    f"{BASE_URL}/tools/call?session_id={SESSION_ID}",
    json={
        "tool_name": "apply_discount",
        "arguments": {"discount_percent": 25}
    }
)
result = response.json()
print(f"Status: {result['status']}")
if result['status'] == 'rejected':
    print(f"  ✗ Rejected (as expected)")
    print(f"    Reason: {result.get('message', 'Unknown')[:80]}...")

# ============================================================================

print("\n--- STEP 4: APPLY VALID DISCOUNT ---")
print("User: Apply a 15% discount\n")

response = requests.post(
    f"{BASE_URL}/tools/call?session_id={SESSION_ID}",
    json={
        "tool_name": "apply_discount",
        "arguments": {"discount_percent": 15}
    }
)
result = response.json()
print(f"Status: {result['status']}")
if result['status'] == 'ok':
    data = result.get('data', {})
    print(f"  ✓ Discount applied")
    print(f"    Subtotal: ₹{data.get('cart_subtotal', 0)}")
    print(f"    Discount: ₹{data.get('discount_amount', 0)}")
    print(f"    Final total: ₹{data.get('cart_total', 0)}")

# ============================================================================

print("\n--- STEP 5: CHECKOUT (Create Razorpay Order) ---")
print("User: Go ahead and checkout\n")

response = requests.post(
    f"{BASE_URL}/tools/call?session_id={SESSION_ID}",
    json={
        "tool_name": "checkout",
        "arguments": {}
    }
)
result = response.json()
print(f"Status: {result['status']}")
if result['status'] == 'ok':
    data = result.get('data', {})
    print(f"  ✓ Order created in Razorpay!")
    print(f"    Order ID: {data.get('razorpay_order_id', 'N/A')}")
    print(f"    Amount: ₹{data.get('amount', 0)}")
    print(f"    Currency: {data.get('currency', 'N/A')}")
    print(f"    Razorpay Key ID: {data.get('razorpay_key_id', 'N/A')[:20]}...")

# ============================================================================

print("\n--- STEP 6: VIEW CART (Verify State) ---")
response = requests.get(f"{BASE_URL}/cart/{SESSION_ID}")
cart_data = response.json()
print(f"\nFinal Cart State:")
print(f"  Items: {len(cart_data.get('items', []))}")
for item in cart_data.get('items', []):
    print(f"    • {item['name']} x{item['quantity']}")
print(f"  Total (with discount): ₹{cart_data.get('total', 0)}")

# ============================================================================

print("\n" + "="*70)
print("✅ DEMO COMPLETE")
print("="*70)
print("\nDemonstrated features:")
print("  ✓ Catalog search")
print("  ✓ Add to cart")
print("  ✓ Discount gating (25% rejected, 15% accepted)")
print("  ✓ Real Razorpay order creation")
print("  ✓ Cart state persistence")
print("\nThis flow can be wrapped in a Groq LLM conversation for natural language.")
print("="*70 + "\n")
