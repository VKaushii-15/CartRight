import React, { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getCart, applyDiscount, removeFromCart, clearCart } from "../api/client";
import { Link } from "react-router-dom";
import { genSessionId } from "../utils/session";
import { getProductImage } from "../utils/imageMap";

export default function CartPage() {
  const qc = useQueryClient();
  const sessionId = genSessionId();
  const { data: cart, isLoading } = useQuery({ queryKey: ["cart", sessionId], queryFn: () => getCart(sessionId) });
  const [discount, setDiscount] = useState("");
  const [discountMsg, setDiscountMsg] = useState(null);
  const [discountError, setDiscountError] = useState(null);
  const [removing, setRemoving] = useState(null);
  const [clearing, setClearing] = useState(false);

  if (isLoading) return <div className="page-wrap"><p style={{color:"var(--muted)"}}>Loading cart...</p></div>;

  const items = cart?.items ?? [];
  const subtotal = cart?.total ?? 0;

  async function handleApply() {
    setDiscountMsg(null); setDiscountError(null);
    try {
      const res = await applyDiscount(sessionId, Number(discount));
      if (res.status === "ok") { setDiscountMsg("Discount applied!"); qc.invalidateQueries(["cart", sessionId]); }
      else setDiscountError(res.message || "Rejected");
    } catch (e) {
      setDiscountError(e?.response?.data?.detail || "Error applying discount");
    }
  }

  async function handleRemove(productId) {
    setRemoving(productId);
    try {
      await removeFromCart(sessionId, productId);
      qc.invalidateQueries(["cart", sessionId]);
    } finally {
      setRemoving(null);
    }
  }

  async function handleClear() {
    setClearing(true);
    try {
      await clearCart(sessionId);
      qc.invalidateQueries(["cart", sessionId]);
    } finally {
      setClearing(false);
    }
  }

  if (!items.length) return (
    <div className="page-wrap">
      <h2 className="page-title">Your Cart</h2>
      <div className="card empty-state">
        <div className="empty-icon">🛒</div>
        <p>Your cart is empty</p>
        <Link to="/shop" className="btn btn-primary" style={{marginTop:8}}>Start Shopping</Link>
      </div>
    </div>
  );

  const emojis = {"Blue Hoodie":"👕","Red T-Shirt":"👔","Black Jeans":"👖","White Sneakers":"👟","Wool Beanie":"🧢"};

  return (
    <div className="page-wrap">
      <div style={{display:"flex", alignItems:"baseline", gap:16, flexWrap:"wrap"}}>
        <h2 className="page-title" style={{margin:0}}>Your Cart</h2>
        <button
          onClick={handleClear}
          disabled={clearing}
          style={{
            marginLeft:"auto", background:"transparent", border:"1px solid var(--red)",
            color:"var(--red)", borderRadius:8, padding:"5px 14px", fontSize:13,
            fontWeight:500, cursor:"pointer", opacity: clearing ? 0.6 : 1
          }}
        >
          {clearing ? "Clearing…" : "🗑 Clear Cart"}
        </button>
      </div>
      <p className="page-sub">{items.length} item{items.length !== 1 ? "s" : ""} in your bag</p>
      <div className="cart-layout">
        <div className="card">
          {items.map((it, i) => {
            const imgSrc = getProductImage(it.name);
            return (
            <div key={i} className="cart-item">
              {imgSrc ? (
                <img src={imgSrc} alt={it.name} className="cart-item-emoji" style={{ objectFit: "cover", width: 48, height: 48, borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center" }} />
              ) : (
                <div className="cart-item-emoji">{emojis[it.name] ?? "📦"}</div>
              )}
              <div className="cart-item-info">
                <div className="cart-item-name">{it.name}</div>
                <div className="cart-item-price">₹{it.price} × {it.quantity}</div>
              </div>
              <div className="cart-item-total">₹{(it.price * it.quantity).toFixed(2)}</div>
              <button
                onClick={() => handleRemove(it.product_id)}
                disabled={removing === it.product_id}
                title="Remove item"
                style={{
                  background:"transparent", border:"none", cursor:"pointer",
                  color:"var(--muted)", fontSize:18, lineHeight:1, padding:"4px 8px",
                  borderRadius:6, transition:"color .15s",
                  opacity: removing === it.product_id ? 0.4 : 1
                }}
                onMouseEnter={e => e.currentTarget.style.color="var(--red)"}
                onMouseLeave={e => e.currentTarget.style.color="var(--muted)"}
              >
                ×
              </button>
            </div>
          )})}
        </div>

        <div className="card summary-card">
          <h3>Order Summary</h3>
          <div className="summary-row"><span>Subtotal</span><span>₹{subtotal.toFixed(2)}</span></div>
          <div className="summary-row"><span>Shipping</span><span style={{color:"var(--green)"}}>Free</span></div>
          <div className="summary-row total"><span>Total</span><span>₹{subtotal.toFixed(2)}</span></div>
          <div className="divider" />
          <div className="section-label">Have a discount?</div>
          <div className="discount-row">
            <input placeholder="0–20%" value={discount} onChange={e => setDiscount(e.target.value)} type="number" min="0" max="20" />
            <button className="btn btn-outline" onClick={handleApply}>Apply</button>
          </div>
          {discountError && <p className="error-msg">✗ {discountError}</p>}
          {discountMsg   && <p className="success-msg">✓ {discountMsg}</p>}
          <Link to="/checkout" className="btn btn-primary btn-full" style={{marginTop:16}}>Proceed to Checkout →</Link>
        </div>
      </div>
    </div>
  );
}
