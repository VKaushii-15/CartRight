"""
Tool calling schemas for LLM-driven tool calls.
Each tool has a request schema that validates LLM-provided arguments.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Any, Literal


# ============================================================================
# Tool Request Schemas (what the LLM provides)
# ============================================================================


class SearchCatalogRequest(BaseModel):
    """Search for products by query string."""
    query: str = Field(..., description="Product name or description keyword to search for")
    limit: int = Field(default=5, ge=1, le=20, description="Max results to return")


class AddToCartRequest(BaseModel):
    """Add a product to the user's cart."""
    product_id: int = Field(..., description="ID of product to add")
    quantity: int = Field(default=1, ge=1, le=10, description="Quantity to add (max 10 per call)")


class ApplyDiscountRequest(BaseModel):
    """Apply a discount percentage to the cart."""
    discount_percent: int = Field(
        ...,
        ge=0,
        le=20,
        description="Discount percentage (0–20% capped by policy)"
    )


class CheckoutRequest(BaseModel):
    """Create a Razorpay order for the current cart."""
    # No parameters — uses session's current cart state


class UpsellSuggestRequest(BaseModel):
    """Suggest related products based on cart contents."""
    # No parameters — uses session's current cart state


# ============================================================================
# Tool Result Schema (unified response from run_tool_call)
# ============================================================================


class ToolCallResult(BaseModel):
    """
    Standard response from run_tool_call().
    Status is "ok" if the tool executed successfully,
    "rejected" if validation or business rule failed.
    """
    status: Literal["ok", "rejected"]
    tool_name: str
    data: Optional[Any] = None  # Tool-specific result data
    message: str = ""  # Human-readable reason or result description


# ============================================================================
# Tool-Specific Result Data Models (nested in ToolCallResult.data)
# ============================================================================


class ProductSearchResult(BaseModel):
    """Result of a successful search_catalog call."""
    id: int
    name: str
    description: str
    price: float
    stock: int


class SearchCatalogResult(BaseModel):
    """Complete result data for search_catalog."""
    query: str
    results: List[ProductSearchResult]
    count: int


class CartItemResult(BaseModel):
    """Item in cart result."""
    product_id: int
    name: str
    price: float
    quantity: int
    subtotal: float


class AddToCartResult(BaseModel):
    """Result after adding item to cart."""
    product_id: int
    quantity: int
    cart_total: float
    cart_item_count: int


class ApplyDiscountResult(BaseModel):
    """Result after applying discount."""
    discount_percent: int
    cart_subtotal: float
    discount_amount: float
    cart_total: float


class CheckoutResult(BaseModel):
    """Result of successful checkout (Razorpay order created)."""
    razorpay_order_id: str
    amount: float  # in paise
    currency: str
    razorpay_key_id: str
    notes: Optional[str] = None


class UpsellSuggestionResult(BaseModel):
    """A product suggestion for upsell."""
    product_id: int
    name: str
    description: str
    price: float
    reason: str  # Why it was suggested


class UpsellSuggestResult(BaseModel):
    """Result of upsell suggestions."""
    suggestions: List[UpsellSuggestionResult]


# ============================================================================
# Constants & Validation Rules
# ============================================================================

ALLOWED_TOOLS = {
    "search_catalog",
    "add_to_cart",
    "apply_discount",
    "checkout",
    "upsell_suggest",
}

MAX_DISCOUNT_PERCENT = 20
MAX_CART_ITEMS = 50
MAX_CART_VALUE_PAISE = 100_000_00  # Rs. 100,000


# Mapping from tool name to its Pydantic request model (used by chat for validation)
TOOL_MODEL_BY_NAME = {
    "search_catalog": SearchCatalogRequest,
    "add_to_cart": AddToCartRequest,
    "apply_discount": ApplyDiscountRequest,
    "checkout": CheckoutRequest,
    "upsell_suggest": UpsellSuggestRequest,
}
