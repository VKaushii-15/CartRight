"""
Gate layer: single entry point for all tool calls.

run_tool_call() validates arguments against tool schemas, executes business logic,
and returns a structured ToolCallResult. Never raises raw exceptions to caller.
"""

from sqlalchemy.orm import Session
from typing import Any, Dict
import json

from app.tools.schemas import (
    SearchCatalogRequest,
    AddToCartRequest,
    ApplyDiscountRequest,
    CheckoutRequest,
    UpsellSuggestRequest,
    ToolCallResult,
    ALLOWED_TOOLS,
    MAX_DISCOUNT_PERCENT,
    ProductSearchResult,
    SearchCatalogResult,
    AddToCartResult,
    ApplyDiscountResult,
    CheckoutResult,
    UpsellSuggestionResult,
    UpsellSuggestResult,
)
from app.models import Cart, CartItem, Product, Order
from app.razorpay_client import create_order, RAZORPAY_KEY_ID


# ============================================================================
# Tool Executor Functions
# ============================================================================


def _search_catalog(args: SearchCatalogRequest, session_id: str, db: Session) -> SearchCatalogResult:
    """Search products by name or description."""
    query_lower = args.query.lower()
    products = db.query(Product).filter(
        (Product.name.ilike(f"%{args.query}%")) |
        (Product.description.ilike(f"%{args.query}%"))
    ).limit(args.limit).all()
    
    results = [
        ProductSearchResult(
            id=p.id,
            name=p.name,
            description=p.description,
            price=p.price,
            stock=p.stock,
        )
        for p in products
    ]
    
    return SearchCatalogResult(
        query=args.query,
        results=results,
        count=len(results),
    )


def _get_or_create_cart(session_id: str, db: Session) -> Cart:
    """Get existing cart or create new one."""
    cart = db.query(Cart).filter(Cart.session_id == session_id).first()
    if not cart:
        cart = Cart(session_id=session_id, discount_percent=0)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


def _get_cart_total(cart: Cart, db: Session) -> float:
    """Calculate cart subtotal (before discount)."""
    total = 0.0
    for item in cart.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            total += product.price * item.quantity
    return total


def _add_to_cart(args: AddToCartRequest, session_id: str, db: Session) -> AddToCartResult:
    """Add product to cart."""
    cart = _get_or_create_cart(session_id, db)
    
    # Verify product exists and has stock
    product = db.query(Product).filter(Product.id == args.product_id).first()
    if not product:
        raise ValueError(f"Product {args.product_id} not found")
    if product.stock < args.quantity:
        raise ValueError(f"Not enough stock for product {args.product_id}. Available: {product.stock}")
    
    # Add or update cart item
    existing = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.product_id == args.product_id,
    ).first()
    
    if existing:
        existing.quantity += args.quantity
    else:
        db.add(CartItem(
            cart_id=cart.id,
            product_id=args.product_id,
            quantity=args.quantity,
        ))
    
    db.commit()
    
    # Calculate new cart totals
    cart_total = _get_cart_total(cart, db)
    cart_item_count = sum(item.quantity for item in cart.items)
    
    return AddToCartResult(
        product_id=args.product_id,
        quantity=args.quantity,
        cart_total=cart_total,
        cart_item_count=cart_item_count,
    )


def _apply_discount(args: ApplyDiscountRequest, session_id: str, db: Session) -> ApplyDiscountResult:
    """Apply discount to cart."""
    # Schema validation already enforced discount_percent <= 20
    # This just applies it to the cart
    cart = _get_or_create_cart(session_id, db)
    cart.discount_percent = args.discount_percent
    db.commit()
    
    cart_subtotal = _get_cart_total(cart, db)
    discount_amount = (cart_subtotal * args.discount_percent) / 100.0
    cart_total = cart_subtotal - discount_amount
    
    return ApplyDiscountResult(
        discount_percent=args.discount_percent,
        cart_subtotal=cart_subtotal,
        discount_amount=discount_amount,
        cart_total=cart_total,
    )


def _checkout(args: CheckoutRequest, session_id: str, db: Session) -> CheckoutResult:
    """Create a Razorpay order for the cart."""
    cart = _get_or_create_cart(session_id, db)
    
    # Verify cart has items
    if not cart.items:
        raise ValueError("Cart is empty")
    
    # Calculate final amount (with discount)
    cart_subtotal = _get_cart_total(cart, db)
    if cart_subtotal <= 0:
        raise ValueError("Cart total must be greater than zero")
    
    discount_amount = (cart_subtotal * cart.discount_percent) / 100.0
    final_amount = cart_subtotal - discount_amount
    
    # Create Razorpay order
    # create_order expects amount in paise (smallest unit of INR)
    rzp_order = create_order(final_amount, receipt=f"cart_{cart.id}")
    
    # Persist order in DB
    order = Order(
        razorpay_order_id=rzp_order["id"],
        cart_id=cart.id,
        amount=final_amount,
        status="created",
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    
    return CheckoutResult(
        razorpay_order_id=rzp_order["id"],
        amount=final_amount,
        currency="INR",
        razorpay_key_id=RAZORPAY_KEY_ID,
    )


def _upsell_suggest(args: UpsellSuggestRequest, session_id: str, db: Session) -> UpsellSuggestResult:
    """Suggest related products based on cart contents."""
    cart = _get_or_create_cart(session_id, db)
    
    # Get product categories from cart
    cart_product_ids = {item.product_id for item in cart.items}
    
    # Simple heuristic: suggest top 3 products not in cart
    # Could be enhanced with actual category/similarity logic
    suggestions = []
    all_products = db.query(Product).filter(~Product.id.in_(cart_product_ids)).limit(3).all()
    
    for product in all_products:
        suggestions.append(UpsellSuggestionResult(
            product_id=product.id,
            name=product.name,
            description=product.description,
            price=product.price,
            reason=f"You might also like {product.name}",
        ))
    
    return UpsellSuggestResult(suggestions=suggestions)


# ============================================================================
# Main Gate Function
# ============================================================================


def run_tool_call(
    tool_name: str,
    arguments: Dict[str, Any],
    session_id: str,
    db: Session,
) -> ToolCallResult:
    """
    Single entry point for all tool calls.
    
    Validates tool name, deserializes arguments into appropriate schema,
    executes business logic, and returns a structured result.
    Never raises raw exceptions to caller.
    
    Args:
        tool_name: Name of tool to execute (must be in ALLOWED_TOOLS)
        arguments: Dict of arguments (will be deserialized into schema)
        session_id: User session ID (injected by server, never from LLM)
        db: SQLAlchemy session
    
    Returns:
        ToolCallResult with status ("ok" or "rejected"), data, and message
    """
    
    # ========== Whitelist Check ==========
    if tool_name not in ALLOWED_TOOLS:
        return ToolCallResult(
            status="rejected",
            tool_name=tool_name,
            message=f"Unknown tool '{tool_name}'. Allowed tools: {', '.join(ALLOWED_TOOLS)}",
        )
    
    try:
        # ========== Schema Validation & Deserialization ==========
        if tool_name == "search_catalog":
            args = SearchCatalogRequest(**arguments)
            result_data = _search_catalog(args, session_id, db)
            
        elif tool_name == "add_to_cart":
            args = AddToCartRequest(**arguments)
            result_data = _add_to_cart(args, session_id, db)
            
        elif tool_name == "apply_discount":
            args = ApplyDiscountRequest(**arguments)
            result_data = _apply_discount(args, session_id, db)
            
        elif tool_name == "checkout":
            args = CheckoutRequest(**arguments)  # No required args
            result_data = _checkout(args, session_id, db)
            
        elif tool_name == "upsell_suggest":
            args = UpsellSuggestRequest(**arguments)  # No required args
            result_data = _upsell_suggest(args, session_id, db)
        
        return ToolCallResult(
            status="ok",
            tool_name=tool_name,
            data=result_data.model_dump(),  # Serialize result to dict
            message=f"Tool '{tool_name}' executed successfully",
        )
    
    except ValueError as e:
        # Business rule violation (e.g., product not found, stock insufficient)
        return ToolCallResult(
            status="rejected",
            tool_name=tool_name,
            message=str(e),
        )
    
    except ValueError as e:
        # Pydantic validation error (e.g., discount > 20%)
        # Extract the first validation error message
        error_msg = str(e)
        return ToolCallResult(
            status="rejected",
            tool_name=tool_name,
            message=f"Invalid arguments: {error_msg}",
        )
    
    except Exception as e:
        # Unexpected error
        return ToolCallResult(
            status="rejected",
            tool_name=tool_name,
            message=f"Tool execution failed: {str(e)}",
        )
