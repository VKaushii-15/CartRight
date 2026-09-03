"""
Groq API client for conversational checkout agent.

Converts tool schemas to OpenAI-compatible format and sends messages to Groq.
"""

import os
import json
import re
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
)
from app.nlu.intent import classify_intent


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
# Allow forcing the local simulator even if GROQ_API_KEY is present
GROQ_FORCE_SIMULATOR = os.getenv("GROQ_FORCE_SIMULATOR", "").lower() in ("1", "true", "yes")

# Model choice: OSS 120B (available on Groq free tier, supports tool-calling well)
GROQ_MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """You are a helpful shopping assistant for an e-commerce store.
Your job is to help users find products, add them to their cart, apply discounts, and checkout.

You have access to the following tools:
- search_catalog: Search for products by name or description
- add_to_cart: Add a product to the user's cart (requires product_id and quantity)
- apply_discount: Apply a discount code to the cart (0-20% only)
- checkout: Create a Razorpay payment order for the cart
- upsell_suggest: Suggest related products based on cart contents

IMPORTANT INSTRUCTIONS:
1. Before calling any tool, reason about the user intent and required fields.
2. If the intent is not clear or a required field is missing, ask a clarifying question instead of guessing.
3. When a user asks to search or find products, use search_catalog with their query.
4. When a user asks to add a product to cart, use add_to_cart with the product ID and quantity.
5. When a user asks for a discount, use apply_discount with the discount percentage (max 20%).
6. When a user asks to checkout or pay, use checkout (no parameters needed).
7. When a user seems interested in more products, use upsell_suggest (no parameters needed).
8. Always try to call the appropriate tool for user requests, not just search.
9. If a tool is rejected, explain the reason and suggest alternatives.
10. Be helpful and guide users through the shopping and checkout process."""


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
        "Search for products by name or description keyword"
    ),
    convert_pydantic_to_groq_schema(
        AddToCartRequest,
        "add_to_cart",
        "Add a product to the user's shopping cart by product ID"
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
            "Show the current cart contents and totals"
        ),
        convert_pydantic_to_groq_schema(
            # Use SearchCatalogRequest's schema for catalog items (same shape)
            SearchCatalogRequest,
            "show_catalog",
            "Show the full product catalog"
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
# Intent Preflight for Tool Calling
# ============================================================================


def preflight_intent_decision(user_message: str) -> Dict[str, Any]:
    """Return a safe routing decision before any tool call is made.

    This creates a thought-like gate: determine intent, required entities,
    and whether the request is clear enough to execute a tool.
    """
    nlu = classify_intent(user_message)
    intent = nlu.get("intent")
    entities = nlu.get("entities", {})
    confidence = nlu.get("confidence", 0.0)
    clarify = nlu.get("clarify")

    if confidence < 0.6 or intent == "unknown":
        return {
            "intent": intent,
            "entities": entities,
            "confidence": confidence,
            "should_call_tool": False,
            "assistant_message": clarify or "Could you clarify what you want me to do?",
        }

    # Enforce a simple safety rule: if a required parameter is missing, ask for it instead
    # of triggering a tool call with guessed values.
    if intent == "add_to_cart" and not entities.get("product_id") and not entities.get("product_name"):
        return {
            "intent": intent,
            "entities": entities,
            "confidence": confidence,
            "should_call_tool": False,
            "assistant_message": "Which product would you like to add? Please provide the product name or product id.",
        }

    if intent == "apply_discount" and "discount_percent" not in entities:
        return {
            "intent": intent,
            "entities": entities,
            "confidence": confidence,
            "should_call_tool": False,
            "assistant_message": "What percentage discount would you like to apply?",
        }

    return {
        "intent": intent,
        "entities": entities,
        "confidence": confidence,
        "should_call_tool": True,
        "assistant_message": "",
    }


# ============================================================================
# Groq API Calling
# ============================================================================

def call_groq(
    user_message: str,
    session_id: str,
    max_tokens: int = 1024,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Send a user message to Groq with tool definitions attached.
    Parse response for tool calls.
    
    Args:
        user_message: User's natural language input
        session_id: Session ID for conversation context
        max_tokens: Max tokens for response
    
    Returns:
        Tuple of (assistant_message, tool_calls)
        where tool_calls is a list of dicts with 'name' and 'arguments'
    """
    
    # Get conversation state and add user message
    conv_state = get_conversation_state(session_id)
    conv_state.add_message("user", user_message)
    # If no real Groq client is configured, or simulator was forced,
    # use a simple deterministic simulator for testing that maps
    # keywords to tool calls.
    # Preflight gating: check intent and required fields before any function call.
    plan = preflight_intent_decision(user_message)
    if not plan["should_call_tool"]:
        assistant_message = plan["assistant_message"]
        conv_state.add_message("assistant", assistant_message)
        return assistant_message, []

    if groq_client is None or GROQ_FORCE_SIMULATOR:
        intent = plan["intent"]
        entities = plan["entities"]
        tool_calls: List[Dict[str, Any]] = []

        if intent == "greeting":
            assistant_message = "Hello! 👋 How can I help you today? Looking for something specific, need product recommendations, or ready to add items to your cart?"
            conv_state.add_message("assistant", assistant_message)
            return assistant_message, []

        if intent == "show_catalog":
            tool_calls.append({"name": "show_catalog", "arguments": {}})
            assistant_message = "Here are the items available in the store..."

        elif intent == "show_cart":
            tool_calls.append({"name": "show_cart", "arguments": {}})
            assistant_message = "Here is your cart..."

        elif intent == "search_catalog":
            q = entities.get("query") or user_message
            tool_calls.append({"name": "search_catalog", "arguments": {"query": q}})
            assistant_message = f"Searching for '{q}'..."

        elif intent == "add_to_cart":
            args = {}
            if entities.get("product_id"):
                args["product_id"] = entities["product_id"]
            if entities.get("quantity"):
                args["quantity"] = entities["quantity"]
            tool_calls.append({"name": "add_to_cart", "arguments": args})
            assistant_message = "Adding item to cart..."

        elif intent == "apply_discount":
            pct = entities["discount_percent"]
            tool_calls.append({"name": "apply_discount", "arguments": {"discount_percent": pct}})
            assistant_message = f"Applying {pct}% discount..."

        elif intent == "checkout":
            tool_calls.append({"name": "checkout", "arguments": {}})
            assistant_message = "Proceeding to checkout..."

        else:
            assistant_message = plan["assistant_message"] or "I didn't quite understand. Could you rephrase?"
            conv_state.add_message("assistant", assistant_message)
            return assistant_message, []

        if assistant_message:
            conv_state.add_message("assistant", assistant_message)

        return assistant_message, tool_calls

    # Real Groq path: keep the model, but force a planning step in the prompt.
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT + "\n\nThink before calling a tool: first infer the user intent, then decide whether a tool is required. If intent is unclear or required parameters are missing, ask a clarifying question instead of guessing."},
            {"role": "user", "content": f"Intent preflight: {plan['intent']} | confidence={plan['confidence']} | entities={plan['entities']}\n\nUser message: {user_message}\n\nIf the intent is unclear or parameters are missing, do not call a function; ask a question instead."},
        ] + conv_state.get_messages(),
        tools=GROQ_TOOLS,
        tool_choice="auto",
        max_tokens=max_tokens,
    )

    # Extract response
    assistant_message = ""
    tool_calls = []

    for choice in response.choices:
        if choice.message.content:
            assistant_message = choice.message.content

        # Check for tool calls in the response
        if choice.message.tool_calls:
            for tool_call in choice.message.tool_calls:
                tool_calls.append({
                    "name": tool_call.function.name,
                    "arguments": json.loads(tool_call.function.arguments),
                })

    # Add assistant message to conversation (without tool calls for clarity)
    if assistant_message:
        conv_state.add_message("assistant", assistant_message)

    return assistant_message, tool_calls


# ============================================================================
# Simple Demo / Testing
# ============================================================================

def chat_with_agent(user_message: str, session_id: str = "default") -> Dict[str, Any]:
    """
    Simplified interface for testing.
    Returns full response including assistant message and any tool calls.
    """
    assistant_message, tool_calls = call_groq(user_message, session_id)
    
    return {
        "user_message": user_message,
        "assistant_message": assistant_message,
        "tool_calls": tool_calls,
        "tool_count": len(tool_calls),
    }
