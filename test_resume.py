#!/usr/bin/env python3
"""
Test clarification + resume flow: create a PendingToolCall then send a user
message that supplies the missing fields and assert the pending call is executed
and removed.
"""

import sys
import json
from sqlalchemy.orm import Session

from app.db import SessionLocal, engine, Base
from app.models import Product, PendingToolCall, CartItem, Cart
from app.routers.chat import chat, ChatRequest


def setup_test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    products = [
        Product(id=1, name="Blue Hoodie", description="Comfortable blue hoodie", price=1500.0, stock=10),
        Product(id=2, name="Red T-Shirt", description="Classic red t-shirt", price=500.0, stock=5),
    ]
    for p in products:
        db.add(p)
    db.commit()
    db.close()


def run_test():
    print("\n--- TEST: Clarify + Resume (Pending add_to_cart) ---")
    setup_test_db()
    db = SessionLocal()

    session_id = "resume_test_session"

    # Create a pending tool-call: add_to_cart missing product_id
    pending = PendingToolCall(
        session_id=session_id,
        tool_name="add_to_cart",
        arguments=json.dumps({}),
        missing_fields=json.dumps(["product_id"]),
    )
    db.add(pending)
    db.commit()

    # Simulate user reply that provides the missing product id and quantity
    request = ChatRequest(message="id 1 quantity 2")

    # Call chat handler directly, passing our DB session
    response = chat(session_id=session_id, request=request, db=db)

    # Inspect response
    assert response.tool_count >= 1, "Expected at least one tool execution"
    execs = response.tool_calls_executed
    found = False
    for e in execs:
        if e.tool_name == "add_to_cart":
            found = True
            assert e.status == "ok", f"Expected add_to_cart to succeed, got {e.status}"
            print("✅ add_to_cart executed and returned ok")

    assert found, "add_to_cart was not executed"

    # Pending should be removed
    pend = db.query(PendingToolCall).filter_by(session_id=session_id).all()
    assert len(pend) == 0, "PendingToolCall was not removed after resume"
    print("✅ PendingToolCall removed after resume")

    # Cart should contain the item
    cart = db.query(Cart).filter_by(session_id=session_id).first()
    assert cart is not None, "Cart was not created"
    items = db.query(CartItem).filter_by(cart_id=cart.id).all()
    assert any(i.product_id == 1 for i in items), "CartItem for product 1 not found"
    print("✅ Cart contains the resumed item (product 1)")

    db.close()
    print("\nTEST PASSED")


if __name__ == "__main__":
    try:
        run_test()
        sys.exit(0)
    except AssertionError as e:
        print("\nTEST FAILED:\n", e)
        sys.exit(1)
