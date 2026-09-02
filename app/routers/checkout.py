from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Cart, Order
from app.schemas import CheckoutResponse, OrderStatusOut
from app.razorpay_client import (
    create_order,
    verify_payment_signature,
    verify_webhook_signature,
    RAZORPAY_KEY_ID,
)
from app.routers.cart import view_cart

router = APIRouter(tags=["checkout"])


@router.post("/cart/{session_id}/checkout", response_model=CheckoutResponse)
def checkout(session_id: str, db: Session = Depends(get_db)):
    cart = db.query(Cart).filter(Cart.session_id == session_id).first()
    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    cart_view = view_cart(session_id, db)
    if cart_view.total <= 0:
        raise HTTPException(status_code=400, detail="Cart total must be greater than zero")

    rzp_order = create_order(cart_view.total, receipt=f"cart_{cart.id}")

    order = Order(
        razorpay_order_id=rzp_order["id"],
        cart_id=cart.id,
        amount=cart_view.total,
        status="created",
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    return CheckoutResponse(
        order_id=order.id,
        razorpay_order_id=rzp_order["id"],
        amount=cart_view.total,
        currency="INR",
        razorpay_key_id=RAZORPAY_KEY_ID,
    )


@router.post("/checkout/verify")
def verify_payment(payload: dict, db: Session = Depends(get_db)):
    """Called by frontend after Checkout.js completes, before trusting success."""
    required = {"razorpay_order_id", "razorpay_payment_id", "razorpay_signature"}
    if not required.issubset(payload):
        raise HTTPException(status_code=400, detail="Missing verification fields")

    order = db.query(Order).filter(Order.razorpay_order_id == payload["razorpay_order_id"]).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if verify_payment_signature(payload):
        order.status = "paid"
        order.razorpay_payment_id = payload["razorpay_payment_id"]
        db.commit()
        return {"status": "verified"}
    else:
        order.status = "failed"
        db.commit()
        raise HTTPException(status_code=400, detail="Signature verification failed")


@router.post("/webhook/razorpay")
async def razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_razorpay_signature: str = Header(None),
):
    """Source of truth for order status — don't rely on frontend callback alone."""
    body = await request.body()
    if not verify_webhook_signature(body, x_razorpay_signature or ""):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    payload = await request.json()
    event = payload.get("event")
    entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    rzp_order_id = entity.get("order_id")

    if rzp_order_id:
        order = db.query(Order).filter(Order.razorpay_order_id == rzp_order_id).first()
        if order:
            if event == "payment.captured":
                order.status = "paid"
                order.razorpay_payment_id = entity.get("id")
            elif event == "payment.failed":
                order.status = "failed"
            db.commit()

    return {"status": "ok"}


@router.get("/orders/{order_id}", response_model=OrderStatusOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderStatusOut(
        order_id=order.id,
        status=order.status,
        amount=order.amount,
        razorpay_order_id=order.razorpay_order_id,
        razorpay_payment_id=order.razorpay_payment_id,
    )
