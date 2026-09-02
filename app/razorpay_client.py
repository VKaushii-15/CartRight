import os
import razorpay
from dotenv import load_dotenv

load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


def create_order(amount_rupees: float, receipt: str) -> dict:
    """Amount must be passed to Razorpay in paise (smallest currency unit)."""
    amount_paise = int(round(amount_rupees * 100))
    return client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "receipt": receipt,
        "payment_capture": 1,
    })


def verify_payment_signature(params: dict) -> bool:
    """params must contain razorpay_order_id, razorpay_payment_id, razorpay_signature."""
    try:
        client.utility.verify_payment_signature(params)
        return True
    except razorpay.errors.SignatureVerificationError:
        return False


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    try:
        client.utility.verify_webhook_signature(
            body.decode("utf-8"), signature, RAZORPAY_WEBHOOK_SECRET
        )
        return True
    except razorpay.errors.SignatureVerificationError:
        return False
