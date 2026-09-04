"""
Groq API client for conversational checkout agent.

Converts tool schemas to OpenAI-compatible format and sends messages to Groq.
"""

import os
import json
from typing import List, Dict, Any, Optional, Tuple
from groq import Groq
from pydantic import BaseModel

# Tool schemas for conversion
from app.tools.schemas import (
    SearchCatalogRequest,
    AddToCartRequest,
    ApplyDiscountRequest,
    CheckoutRequest,
    UpsellSuggestRequest,
    ShowCartRequest,
    ShowCatalogRequest,
    RemoveFromCartRequest,
    ClearCartRequest,
)


# ============================================================================
# Groq Client Initialization
# ============================================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)
else:
    # Allow running in offline/test environments without raising on import.
    # When `groq_client` is None, `call_groq` will use a simple deterministic
    # simulator to produce tool calls from user messages so unit/integration
    # tests can run without a real Groq API key.
    groq_client = None
# Optional offline test hook left here for dedicated test scripts only.
# Production behavior should *not* silently switch to a fake keyword simulator.
GROQ_FORCE_SIMULATOR = os.getenv("GROQ_FORCE_SIMULATOR", "").lower() in ("1", "true", "yes")

# Model choice: OSS 120B (available on Groq free tier, supports tool-calling well)
GROQ_MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """You are a helpful shopping assistant for an e-commerce store.
Your job is to help users find products, add them to their cart, apply discounts, and checkout.

You have access to the following tools:
- search_catalog: Search for products by name or description keyword. Use this to find product IDs.
- add_to_cart: Add a specific product to the user's cart. REQUIRES a product_id (integer). If the user says "add X" but you don't have the product_id yet, call search_catalog first to find it, then call add_to_cart with the correct product_id.
- remove_from_cart: Remove a specific product from the cart. REQUIRES product_id. If you don't know the product_id, call show_cart first to see what's in the cart.
- clear_cart: Remove ALL items from the cart at once (no parameters needed).
- apply_discount: Apply a discount percentage to the cart (0-20% only).
- checkout: Create a Razorpay payment order for the cart (no parameters needed).
- upsell_suggest: Suggest related products based on cart contents (no parameters needed).
- show_cart: View the current cart contents and totals (no parameters needed).
- show_catalog: View the full product catalog (no parameters needed).

IMPORTANT RULES:
1. Reason about intent before calling any tool.
2. If the user wants to add something to cart but hasn't specified a product, ask them what product they want or call search_catalog to find it — never call add_to_cart with a made-up product_id.
3. For "add X to cart" messages, call search_catalog for X first to get the product_id, then call add_to_cart.
4. For "remove X from cart" messages, call show_cart first if you don't know the product_id, then call remove_from_cart.
5. For "clear cart" or "empty my cart", call clear_cart directly.
6. If the request is ambiguous or a required field is truly missing, ask a clarifying question.
7. When a user asks to checkout or pay, use checkout.
8. When a user asks to view their cart or basket, use show_cart.
9. When a user wants to browse all products, use show_catalog.
10. If a tool is rejected, explain why and suggest alternatives.
11. Guide users naturally through the shopping and checkout flow."""


# ============================================================================
# Tool Schema Conversion
# ============================================================================

def convert_pydantic_to_groq_schema(
    pydantic_model: type[BaseModel],
    tool_name: str,
    tool_description: str,
) -> Dict[str, Any]:
    """
    Convert a Pydantic model to Groq's OpenAI-compatible function schema.
    
    Args:
        pydantic_model: Pydantic BaseModel class
        tool_name: Name of the tool
        tool_description: Description of what the tool does
    
    Returns:
        Groq function schema dict
    """
    # Get Pydantic schema (v2 format)
    schema = pydantic_model.model_json_schema()
    
    return {
        "type": "function",
        "function": {
            "name": tool_name,
            "description": tool_description,
            "parameters": {
                "type": "object",
                "properties": schema.get("properties", {}),
                "required": schema.get("required", []),
            },
        },
    }


# ============================================================================
# Tool Definitions
# ============================================================================

GROQ_TOOLS = [
    convert_pydantic_to_groq_schema(
        SearchCatalogRequest,
        "search_catalog",
        "Search for products by name or description keyword. Returns product IDs needed for add_to_cart."
    ),
    convert_pydantic_to_groq_schema(
        AddToCartRequest,
        "add_to_cart",
        "Add a product to the user's shopping cart. Requires product_id (integer) — search first if you don't have it."
    ),
    convert_pydantic_to_groq_schema(
        ApplyDiscountRequest,
        "apply_discount",
        "Apply a discount percentage to the cart (0-20% only, policy enforced)"
    ),
    convert_pydantic_to_groq_schema(
        CheckoutRequest,
        "checkout",
        "Create a Razorpay order for the current cart (no parameters needed)"
    ),
    convert_pydantic_to_groq_schema(
        UpsellSuggestRequest,
        "upsell_suggest",
        "Get product suggestions based on what's in the cart (no parameters needed)"
    ),
    convert_pydantic_to_groq_schema(
        ShowCartRequest,
        "show_cart",
        "Show the current cart contents and totals (no parameters needed)"
    ),
    convert_pydantic_to_groq_schema(
        ShowCatalogRequest,
        "show_catalog",
        "Show the full product catalog (no parameters needed)"
    ),
    convert_pydantic_to_groq_schema(
        RemoveFromCartRequest,
        "remove_from_cart",
        "Remove a specific product from the cart by product_id. Call show_cart first if you don't know the product_id."
    ),
    convert_pydantic_to_groq_schema(
        ClearCartRequest,
        "clear_cart",
        "Remove ALL items from the cart at once (no parameters needed)"
    ),
]


# ============================================================================
# Message History Management
# ============================================================================

class ConversationState:
    """In-memory conversation state (for testing/demo purposes)."""
    
    def __init__(self):
        self.messages: List[Dict[str, str]] = []
    
    def add_message(self, role: str, content: str):
        """Add a message to the conversation."""
        self.messages.append({"role": role, "content": content})
    
    def get_messages(self) -> List[Dict[str, str]]:
        """Get all messages in the conversation."""
        return self.messages.copy()
    
    def clear(self):
        """Clear conversation history."""
        self.messages.clear()


# Per-session conversation state
_conversation_states: Dict[str, ConversationState] = {}


def get_conversation_state(session_id: str) -> ConversationState:
    """Get or create conversation state for a session."""
    if session_id not in _conversation_states:
        _conversation_states[session_id] = ConversationState()
    return _conversation_states[session_id]


# ============================================================================
# Groq API Calling
# ============================================================================

def call_groq(
    user_message: str,
    session_id: str,
    max_tokens: int = 1024,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Single-turn call to Groq. Records the user message, sends the full
    conversation + tools, and returns (assistant_text, tool_call_list).
    """
    conv_state = get_conversation_state(session_id)
    conv_state.add_message("user", user_message)

    if groq_client is None:
        assistant_message = (
            "Groq is not configured in this environment. "
            "Set GROQ_API_KEY or use a dedicated offline simulator in a test script."
        )
        conv_state.add_message("assistant", assistant_message)
        return assistant_message, []

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
        ] + conv_state.get_messages(),
        tools=GROQ_TOOLS,
        tool_choice="auto",
        max_tokens=max_tokens,
    )

    assistant_message = ""
    tool_calls = []

    for choice in response.choices:
        if choice.message.content:
            assistant_message = choice.message.content
        if choice.message.tool_calls:
            for tool_call in choice.message.tool_calls:
                tool_calls.append({
                    "id": tool_call.id,
                    "name": tool_call.function.name,
                    "arguments": json.loads(tool_call.function.arguments),
                })

    if assistant_message:
        conv_state.add_message("assistant", assistant_message)

    return assistant_message, tool_calls


def call_groq_with_tool_results(
    tool_results: List[Dict[str, Any]],
    session_id: str,
    max_tokens: int = 1024,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    After executing tool calls, feed their results back to Groq so it can
    decide to call more tools or give a final plain-text answer.

    tool_results is a list of dicts:
        {"tool_call_id": str, "name": str, "content": str}
    """
    conv_state = get_conversation_state(session_id)

    if groq_client is None:
        return "", []

    # Build messages: system + history + tool result messages
    tool_messages = [
        {"role": "tool", "tool_call_id": r["tool_call_id"], "name": r["name"], "content": r["content"]}
        for r in tool_results
    ]

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
        ] + conv_state.get_messages() + tool_messages,
        tools=GROQ_TOOLS,
        tool_choice="auto",
        max_tokens=max_tokens,
    )

    assistant_message = ""
    tool_calls = []

    for choice in response.choices:
        if choice.message.content:
            assistant_message = choice.message.content
        if choice.message.tool_calls:
            for tool_call in choice.message.tool_calls:
                tool_calls.append({
                    "id": tool_call.id,
                    "name": tool_call.function.name,
                    "arguments": json.loads(tool_call.function.arguments),
                })

    if assistant_message:
        conv_state.add_message("assistant", assistant_message)

    return assistant_message, tool_calls

