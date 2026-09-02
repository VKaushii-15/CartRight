#!/usr/bin/env python3
"""
Integration test for Phase 3: Full conversational checkout flow.
Multi-turn conversation: search → add → discount → checkout
Verifies Groq tool-calling and gate layer execution end-to-end.
"""

import sys
from sqlalchemy.orm import Session

from app.db import SessionLocal, engine, Base
from app.models import Product
from app.routers.chat import chat, ChatRequest
from app.groq_client import get_conversation_state

# Dependency injection for testing
class DependencyOverride:
    def __init__(self, db: Session):
        self.db = db

def get_db_override():
    return DependencyOverride.db_instance

def setup_test_db():
    """Create fresh test database and seed with products."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Seed test products
    products = [
        Product(id=1, name="Blue Hoodie", description="Comfortable blue cotton hoodie", price=1500.0, stock=10),
        Product(id=2, name="Red T-Shirt", description="Classic red crew neck t-shirt", price=500.0, stock=5),
        Product(id=3, name="Black Jeans", description="Slim fit black denim jeans", price=2500.0, stock=3),
        Product(id=4, name="White Sneakers", description="Casual white athletic sneakers", price=3500.0, stock=8),
        Product(id=5, name="Wool Beanie", description="Warm wool winter beanie", price=800.0, stock=15),
    ]
    for p in products:
        db.add(p)
    db.commit()
    db.close()


def run_conversation_test():
    """Run a multi-turn conversation test."""
    print("\n" + "="*70)
    print("PHASE 3 INTEGRATION TEST: CONVERSATIONAL CHECKOUT")
    print("="*70 + "\n")
    
    setup_test_db()
    db = SessionLocal()
    session_id = "test_conversation_1"
    
    # Clear any previous conversation state
    if session_id in dir():
        from app.groq_client import _conversation_states
        _conversation_states.pop(session_id, None)
    
    test_messages = [
        "I'm looking for a comfortable hoodie",
        "Can you add the blue hoodie? I want one size medium",
        "Apply a 15% discount for me",
        "Go ahead and checkout",
    ]
    
    conversation_history = []
    all_tools_executed = []
    
    print(f"Starting conversation (Session: {session_id})\n")
    
    for i, user_message in enumerate(test_messages, 1):
        print(f"--- Turn {i} ---")
        print(f"User: {user_message}")
        
        try:
            # Send message to chat endpoint
            response = chat(
                session_id=session_id,
                request=ChatRequest(message=user_message),
                db=db,
            )
            
            conversation_history.append({
                "turn": i,
                "user": user_message,
                "assistant": response.assistant_message,
                "tools_executed": response.tool_calls_executed,
                "status": response.status,
            })
            
            # Print response
            if response.assistant_message:
                print(f"Assistant: {response.assistant_message}\n")
            
            # Print tool executions
            if response.tool_count > 0:
                print(f"Tools executed ({response.tool_count}):")
                for execution in response.tool_calls_executed:
                    all_tools_executed.append({
                        "turn": i,
                        "tool": execution.tool_name,
                        "status": execution.status,
                        "result": execution.result,
                    })
                    status_emoji = "✅" if execution.status == "ok" else "❌"
                    print(f"  {status_emoji} {execution.tool_name}: {execution.message}")
                    if execution.result:
                        print(f"     Data: {str(execution.result)[:100]}...")
                print()
            
            # Check if conversation should continue
            if response.status == "partial":
                print("⚠️  Some tools were rejected. Continuing anyway...\n")
        
        except Exception as e:
            print(f"❌ Error on turn {i}: {str(e)}\n")
            db.close()
            return False
    
    db.close()
    
    # ========== Verification ==========
    print("="*70)
    print("CONVERSATION SUMMARY")
    print("="*70)
    
    print(f"Total turns: {len(conversation_history)}")
    print(f"Total tool executions: {len(all_tools_executed)}")
    
    # Verify key tools were called
    tool_names = {t["tool"] for t in all_tools_executed}
    print(f"\nTools called: {', '.join(sorted(tool_names))}")
    
    expected_tools = {"search_catalog", "add_to_cart", "apply_discount", "checkout"}
    if expected_tools.issubset(tool_names):
        print(f"✅ All expected tools were called")
    else:
        missing = expected_tools - tool_names
        print(f"❌ Missing tools: {missing}")
    
    # Count successes
    successful_tools = [t for t in all_tools_executed if t["status"] == "ok"]
    print(f"\n✅ Successful tool calls: {len(successful_tools)}")
    
    if successful_tools:
        print("\nSuccessful executions:")
        for t in successful_tools:
            print(f"  - Turn {t['turn']}: {t['tool']}")
    
    # Check for checkout success
    checkout_calls = [t for t in all_tools_executed if t["tool"] == "checkout"]
    if checkout_calls and checkout_calls[0]["status"] == "ok":
        checkout_result = checkout_calls[0]["result"]
        if "razorpay_order_id" in checkout_result:
            print(f"\n✅ CHECKOUT SUCCESSFUL!")
            print(f"   Razorpay Order ID: {checkout_result['razorpay_order_id']}")
            print(f"   Amount: ₹{checkout_result.get('amount', 'N/A')}")
            return True
    
    print(f"\n❌ Checkout did not succeed")
    return False


if __name__ == "__main__":
    success = run_conversation_test()
    
    print("\n" + "="*70)
    if success:
        print("✅ INTEGRATION TEST PASSED")
        sys.exit(0)
    else:
        print("❌ INTEGRATION TEST FAILED")
        sys.exit(1)
