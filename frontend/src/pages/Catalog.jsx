import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchCatalog } from "../api/client";
import { Link } from "react-router-dom";

const emojis = {"Blue Hoodie":"👕","Red T-Shirt":"👔","Black Jeans":"👖","White Sneakers":"👟","Wool Beanie":"🧢"};

export default function Catalog() {
  const [q, setQ] = useState("");
  const { data, isLoading } = useQuery({
    queryKey: ["catalog", q],
    queryFn: () => fetchCatalog(q),
    placeholderData: prev => prev,
  });

  const products = Array.isArray(data) ? data : [];

  return (
    <div className="page-wrap">
      <div className="catalog-header">
        <h2>Shop All Products</h2>
        <p>Discover our handpicked collection</p>
      </div>

      <div className="search-bar">
        <span className="search-icon">🔍</span>
        <input
          value={q}
          onChange={e => setQ(e.target.value)}
          placeholder="Search products…"
        />
        {q && <button style={{background:"none",border:"none",color:"var(--muted)",cursor:"pointer",fontSize:16}} onClick={() => setQ("")}>×</button>}
      </div>

      {isLoading && (
        <div className="product-grid">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="card product-card">
              <div className="skeleton" style={{height:190}} />
              <div style={{padding:16}}><div className="skeleton" style={{height:16,marginBottom:8}} /><div className="skeleton" style={{height:12,width:"60%"}} /></div>
            </div>
          ))}
        </div>
      )}

      {!isLoading && products.length === 0 && (
        <div className="card empty-state">
          <div className="empty-icon">🔍</div>
          <p>No products found for &ldquo;{q}&rdquo;</p>
          <button className="btn btn-outline" onClick={() => setQ("")}>Clear Search</button>
        </div>
      )}

      <div className="product-grid">
        {products.map(p => (
          <div key={p.id} className="card product-card">
            <div className="product-img">{emojis[p.name] ?? "📦"}</div>
            <div className="product-body">
              <div className="product-name">{p.name}</div>
              <div className="product-desc">{p.description}</div>
              <div className="product-footer">
                <div className="product-price">₹{p.price}</div>
                <span className={`stock-badge ${p.stock > 3 ? "in-stock" : "low-stock"}`}>
                  {p.stock > 3 ? `${p.stock} left` : p.stock === 0 ? "Sold out" : `Only ${p.stock}`}
                </span>
              </div>
              <Link to={`/product/${p.id}`} className="btn btn-primary" style={{marginTop:14,width:"100%"}}>View Product</Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
