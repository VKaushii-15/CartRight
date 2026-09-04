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
  const [receipt, setReceipt] = useState(null);

  async function handleCheckout() {
    setLoading(true); setError(null);
    try {
      const currentCart = qc.getQueryData(["cart", sessionId]);
      const res = await checkout(sessionId);
      if (res?.razorpay_order_id) {
        setOrderId(res.razorpay_order_id);
        if (currentCart) setReceipt(currentCart);
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
      <div className="card order-confirm" style={{ padding: "48px 24px", maxWidth: 600, margin: "0 auto" }}>
        <div className="confirm-icon">🎉</div>
        <h2>Order Placed!</h2>
        <p>Your Razorpay test-mode order was created successfully.</p>
        <div className="order-id">Order ID: {orderId}</div>

        {receipt && (
          <div style={{ textAlign: "left", background: "var(--card2)", padding: 24, borderRadius: "var(--radius)", margin: "24px 0" }}>
            <h3 style={{ marginTop: 0, marginBottom: 16 }}>Receipt</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {receipt.items.map((it, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: 12, borderBottom: "1px solid var(--border)" }}>
                  <div>
                    <div style={{ fontWeight: 600 }}>{it.name}</div>
                    <div style={{ fontSize: 13, color: "var(--text-sm)" }}>Qty: {it.quantity}</div>
                  </div>
                  <div style={{ fontWeight: 700 }}>₹{(it.price * it.quantity).toFixed(2)}</div>
                </div>
              ))}
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 16, fontSize: 18, fontWeight: 800 }}>
              <span>Total Paid</span>
              <span style={{ color: "var(--accent)" }}>₹{receipt.total.toFixed(2)}</span>
            </div>
          </div>
        )}

        <Link to="/" className="btn btn-primary" style={{ width: "100%" }}>Continue Shopping</Link>
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
