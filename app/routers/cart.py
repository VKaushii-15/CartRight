from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Cart, CartItem, Product
from app.schemas import AddToCartRequest, CartOut, CartItemOut
from app.tools import run_tool_call
from app.tools.schemas import ToolCallResult

router = APIRouter(prefix="/cart", tags=["cart"])


def get_or_create_cart(session_id: str, db: Session) -> Cart:
    cart = db.query(Cart).filter(Cart.session_id == session_id).first()
    if not cart:
        cart = Cart(session_id=session_id, discount_percent=0)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


@router.get("/{session_id}", response_model=CartOut)
def view_cart(session_id: str, db: Session = Depends(get_db)):
    cart = get_or_create_cart(session_id, db)
    items = []
    subtotal = 0.0
    for item in cart.items:
        items.append(CartItemOut(
            product_id=item.product_id,
            name=item.product.name,
            price=item.product.price,
            quantity=item.quantity,
        ))
        subtotal += item.product.price * item.quantity
    
    # Apply discount if set
    discount_amount = (subtotal * cart.discount_percent) / 100.0
    total = subtotal - discount_amount
    
    return CartOut(session_id=session_id, items=items, total=total)


@router.post("/{session_id}/add", response_model=CartOut)
def add_to_cart(session_id: str, req: AddToCartRequest, db: Session = Depends(get_db)):
    cart = get_or_create_cart(session_id, db)
    product = db.query(Product).filter(Product.id == req.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.stock < req.quantity:
        raise HTTPException(status_code=400, detail="Not enough stock")

    existing = db.query(CartItem).filter(
        CartItem.cart_id == cart.id, CartItem.product_id == req.product_id
    ).first()
    if existing:
        existing.quantity += req.quantity
    else:
        db.add(CartItem(cart_id=cart.id, product_id=req.product_id, quantity=req.quantity))
    db.commit()

    return view_cart(session_id, db)


@router.post("/{session_id}/clear", response_model=CartOut)
def clear_cart(session_id: str, db: Session = Depends(get_db)):
    cart = get_or_create_cart(session_id, db)
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    db.commit()
    return view_cart(session_id, db)


@router.post("/{session_id}/remove/{product_id}", response_model=CartOut)
def remove_from_cart(session_id: str, product_id: int, db: Session = Depends(get_db)):
    cart = get_or_create_cart(session_id, db)
    item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id, CartItem.product_id == product_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not in cart")
    db.delete(item)
    db.commit()
    return view_cart(session_id, db)


@router.post("/{session_id}/apply_discount", response_model=ToolCallResult)
def apply_discount(
    session_id: str,
    discount_percent: int,
    db: Session = Depends(get_db),
):
    """
    Apply a discount percentage to the cart.
    Validates discount is 0-20% and updates cart state.
    """
    result = run_tool_call(
        tool_name="apply_discount",
        arguments={"discount_percent": discount_percent},
        session_id=session_id,
        db=db,
    )
    return result
