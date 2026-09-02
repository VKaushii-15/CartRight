from pydantic import BaseModel
from typing import List, Optional


class ProductOut(BaseModel):
    id: int
    name: str
    description: str
    price: float
    stock: int

    class Config:
        from_attributes = True


class AddToCartRequest(BaseModel):
    product_id: int
    quantity: int = 1


class CartItemOut(BaseModel):
    product_id: int
    name: str
    price: float
    quantity: int


class CartOut(BaseModel):
    session_id: str
    items: List[CartItemOut]
    total: float


class CheckoutResponse(BaseModel):
    order_id: int
    razorpay_order_id: str
    amount: float
    currency: str
    razorpay_key_id: str


class OrderStatusOut(BaseModel):
    order_id: int
    status: str
    amount: float
    razorpay_order_id: Optional[str]
    razorpay_payment_id: Optional[str]
