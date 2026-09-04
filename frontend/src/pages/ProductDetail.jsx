import React, { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchProduct, addToCart } from "../api/client";
import { genSessionId } from "../utils/session";
import { getProductImage } from "../utils/imageMap";

export default function ProductDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const sessionId = genSessionId();
  const { data: product, isLoading } = useQuery({ queryKey: ["product", id], queryFn: () => fetchProduct(id) });
  const [qty, setQty] = useState(1);
  const [adding, setAdding] = useState(false);

  if (isLoading) return <div className="page-wrap"><p style={{color:"var(--muted)"}}>Loading product...</p></div>;
  if (!product)  return <div className="page-wrap"><p style={{color:"var(--muted)"}}>Product not found.</p></div>;

  const imgSrc = getProductImage(product.name);
  const emojis = {"Blue Hoodie":"👕","Red T-Shirt":"👔","Black Jeans":"👖","White Sneakers":"👟","Wool Beanie":"🧢"};
  const emoji = emojis[product.name] ?? "📦";

  async function handleAdd() {
    setAdding(true);
    await addToCart(sessionId, product.id, qty);
    qc.invalidateQueries(["cart", sessionId]);
    navigate("/cart");
  }

  return (
    <div className="page-wrap">
      <div className="detail-grid">
        {imgSrc ? (
          <img src={imgSrc} alt={product.name} className="detail-img" style={{ objectFit: "cover", width: "100%" }} />
        ) : (
          <div className="detail-img">{emoji}</div>
        )}
        <div className="detail-body">
          <h2>{product.name}</h2>
          <p className="detail-desc">{product.description}</p>
          <div className="detail-price">₹{product.price}</div>
          <span className={`stock-badge ${product.stock > 3 ? "in-stock" : "low-stock"}`}>
            {product.stock > 0 ? `${product.stock} in stock` : "Out of stock"}
          </span>
          <div className="qty-row" style={{marginTop:20}}>
            <button className="qty-btn" onClick={() => setQty(q => Math.max(1, q - 1))}>−</button>
            <span className="qty-val">{qty}</span>
            <button className="qty-btn" onClick={() => setQty(q => Math.min(product.stock, q + 1))}>+</button>
          </div>
          <button
            className="btn btn-primary"
            onClick={handleAdd}
            disabled={adding || product.stock === 0}
            style={{width:"100%"}}
          >
            {adding ? "Adding..." : "🛒  Add to Cart"}
          </button>
        </div>
      </div>
    </div>
  );
}
