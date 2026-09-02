import React, { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { checkout } from "../api/client";
import { useNavigate, Link } from "react-router-dom";
import { genSessionId } from "../utils/session";

export default function Checkout() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const sessionId = genSessionId();
  const [loading, setLoading] = useState(false);
  const [orderId, setOrderId] = useState(null);
  const [error, setError] = useState(null);

  async function handleCheckout() {
    setLoading(true); setError(null);
    try {
      const res = await checkout(sessionId);
      if (res?.razorpay_order_id) {
        setOrderId(res.razorpay_order_id);
        qc.invalidateQueries(["cart", sessionId]);
      } else {
        setError(res?.message || "Checkout failed — cart may be empty.");
      }
    } catch (e) {
      setError(e?.response?.data?.detail || "Checkout failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  if (orderId) return (
    <div className="page-wrap">
      <div className="card order-confirm">
        <div className="confirm-icon">🎉</div>
        <h2>Order Placed!</h2>
        <p>Your Razorpay test-mode order was created successfully.</p>
        <div className="order-id">Order ID: {orderId}</div>
        <Link to="/" className="btn btn-primary">Continue Shopping</Link>
      </div>
    </div>
  );

  return (
    <div className="page-wrap">
      <div className="checkout-wrap">
        <h2 className="page-title">Checkout</h2>
        <p className="page-sub">Review and confirm your order</p>

        <div className="checkout-step"><div className="step-icon">🔒</div><span>Secure checkout via Razorpay test mode</span></div>
        <div className="checkout-step"><div className="step-icon">📦</div><span>Free delivery on all orders</span></div>
        <div className="checkout-step"><div className="step-icon">↩️</div><span>Easy 30-day returns</span></div>

        {error && <p className="error-msg" style={{marginTop:16}}>✗ {error}</p>}

        <button
          className="btn btn-primary btn-full"
          style={{marginTop:28,padding:"14px",fontSize:16}}
          onClick={handleCheckout}
          disabled={loading}
        >
          {loading ? "Placing order..." : "Place Order →"}
        </button>
        <Link to="/cart" className="btn btn-ghost btn-full" style={{marginTop:10}}>← Back to Cart</Link>
      </div>
    </div>
  );
}
