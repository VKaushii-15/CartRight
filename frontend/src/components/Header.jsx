import React from "react";
import { NavLink, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getCart } from "../api/client";
import { genSessionId } from "../utils/session";

export default function Header() {
  const sessionId = genSessionId();
  const { data: cart } = useQuery({ queryKey: ["cart", sessionId], queryFn: () => getCart(sessionId), refetchInterval: 10000 });
  const itemCount = cart?.items?.reduce((s, i) => s + i.quantity, 0) ?? 0;

  return (
    <header className="header">
      <div className="header-inner">
        <Link to="/" className="header-logo">🛒 CartRight</Link>
        <nav className="header-nav">
          <NavLink to="/" end className={({isActive}) => `nav-link${isActive ? " active" : ""}` }>Shop</NavLink>
          <NavLink to="/chat"    className={({isActive}) => `nav-link${isActive ? " active" : ""}`}>Assistant</NavLink>
        </nav>
        <NavLink to="/cart" className={({isActive}) => `cart-badge${isActive ? " active" : ""}`}>
          <span className="dot" />
          Cart {itemCount > 0 && <strong>({itemCount})</strong>}
        </NavLink>
      </div>
    </header>
  );
}
