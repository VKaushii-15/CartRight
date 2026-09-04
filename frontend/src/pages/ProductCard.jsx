import React from "react";
import { Link } from "react-router-dom";
import { getProductImage } from "../utils/imageMap";

export default function ProductCard({ product }) {
  const imgSrc = getProductImage(product.name);
  
  return (
    <div style={{ background: "#0f172a", padding: 12, borderRadius: 8, color: "#e6eef8" }}>
      {imgSrc ? (
        <img 
          src={imgSrc} 
          alt={product.name} 
          style={{ width: "100%", height: 140, objectFit: "cover", borderRadius: 6, marginBottom: 8 }} 
        />
      ) : (
        <div style={{ height: 140, background: "#081328", borderRadius: 6, marginBottom: 8 }} />
      )}
      <div style={{ fontWeight: 600 }}>{product.name}</div>
      <div style={{ color: "#9ca3af", fontSize: 13 }}>{product.description}</div>
      <div style={{ marginTop: 8, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>₹{product.price}</div>
        <Link to={`/product/${product.id}`} style={{ color: "#60a5fa" }}>View</Link>
      </div>
    </div>
  );
}
