import React, { useEffect, useRef, useState } from "react";
import { genSessionId } from "../utils/session";
import { sendChatMessage } from "../api/client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function ChatAssistant() {
  const [sessionId] = useState(genSessionId);
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem(`chat_history_${sessionId}`);
    if (saved) return JSON.parse(saved);
    return [
      { role: "assistant", content: "Hi! I'm your shopping assistant 🛍️\nTell me what you're looking for — I can search products, add items to your cart, apply discounts, and checkout for you!" }
    ];
  });
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => { 
    localStorage.setItem(`chat_history_${sessionId}`, JSON.stringify(messages));
    bottomRef.current?.scrollIntoView({ behavior: "smooth" }); 
  }, [messages, sessionId]);

  async function sendMessage() {
    const text = input.trim();
    if (!text || loading) return;
    setMessages(m => [...m, { role: "user", content: text }]);
    setInput("");
    setLoading(true);
    try {
      const data = await sendChatMessage(sessionId, text);

      // If the backend didn't return assistant text, synthesize a helpful
      // summary from executed tool calls so users see meaningful output.
      function summarizeTools(tools) {
        if (!tools || tools.length === 0) return "Done!";
        const parts = [];
        for (const t of tools) {
            if (t.tool_name === "show_cart") {
              try {
                const items = t.result?.items || [];
                if (items.length === 0) {
                  parts.push("Your cart is empty");
                  continue;
                }
                const list = items.map(it => `${it.quantity}× ${it.name} (₹${it.price})`).join("; ");
                parts.push(`Cart: ${list} (subtotal: ₹${t.result?.subtotal || '0'}, total: ₹${t.result?.total || '0'})`);
                continue;
              } catch (e) { parts.push("Cart summary"); }
            }
              if (t.tool_name === "show_catalog") {
                try {
                  const items = t.result?.items || [];
                  if (items.length === 0) {
                    parts.push("No products found in catalog");
                    continue;
                  }
                  const list = items.map(it => `${it.id}: ${it.name} — ₹${it.price} (${it.stock} in stock)`).join("; ");
                  parts.push(`Catalog: ${list}`);
                  continue;
                } catch (e) { parts.push("Catalog summary"); }
              }
          if (t.tool_name === "search_catalog") {
            try {
              const q = t.arguments?.query || "";
              const count = t.result?.count ?? null;
              parts.push(count !== null ? `Found ${count} results for "${q}"` : `Searched for "${q}"`);
            } catch (e) { parts.push("Searched catalog"); }
          } else if (t.tool_name === "add_to_cart") {
            const qty = t.arguments?.quantity ?? t.result?.quantity ?? 1;
            const pid = t.arguments?.product_id ?? t.result?.product_id;
            const total = t.result?.cart_total;
            parts.push(`Added ${qty} × product ${pid} to cart${total ? ` (cart total: ₹${total})` : ""}`);
          } else if (t.tool_name === "apply_discount") {
            const code = t.arguments?.code ?? t.result?.code;
            const pct = t.result?.discount_percent;
            const cartTotal = t.result?.cart_total;
            parts.push(t.status === "ok"
              ? `Applied code ${code} (${pct}% off)${cartTotal ? ` (new total: ₹${cartTotal})` : ""}`
              : `Could not apply code: ${t.message}`);
          } else if (t.tool_name === "checkout") {
            const oid = t.result?.razorpay_order_id || t.result?.order_id;
            const amt = t.result?.amount;
            parts.push(oid ? `Checkout: order ${oid}${amt ? ` (₹${amt})` : ""}` : `Checkout completed`);
          } else if (t.tool_name === "upsell_suggest") {
            parts.push("Suggested related products");
          } else if (t.tool_name === "remove_from_cart") {
            const pid = t.arguments?.product_id ?? t.result?.product_id;
            const total = t.result?.cart_total;
            parts.push(t.status === "ok"
              ? `Removed product ${pid} from cart${total !== undefined ? ` (cart total: ₹${total})` : ""}`
              : `Could not remove product ${pid}: ${t.message}`);
          } else if (t.tool_name === "clear_cart") {
            const n = t.result?.items_removed;
            parts.push(t.status === "ok"
              ? `Cart cleared${n !== undefined ? ` (${n} item${n !== 1 ? "s" : ""} removed)` : ""}`
              : `Could not clear cart: ${t.message}`);
          } else {
            parts.push(`${t.tool_name} → ${t.status}`);
          }
        }
        return parts.join("; ");
      }

      const reply = data.assistant_message || summarizeTools(data.tool_calls_executed);
      setMessages(m => [...m, { role: "assistant", content: reply, tools: data.tool_calls_executed }]);
    } catch (e) {
      const detail = e?.response?.data?.detail || e?.message || "Unknown error";
      setMessages(m => [...m, { role: "assistant", content: `⚠️ Server error: ${detail}\n\nMake sure the backend is running on port 8000.` }]);
    } finally {
      setLoading(false);
    }
  }

  function onKey(e) { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }

  return (
    <div className="page-wrap" style={{padding:"24px 20px 0"}}>
      <div className="chat-shell">
        <div className="chat-topbar">
          <div className="chat-avatar">🤖</div>
          <div className="chat-topbar-info">
            <div className="name">CartRight Assistant</div>
            <div className="status">● Online</div>
          </div>
        </div>

        <div className="messages-wrap">
          {messages.map((m, i) => (
            <div key={i} className={`bubble-row ${m.role}`}>
              {m.role === "assistant" && <div className="bubble-avatar">🤖</div>}
              <div>
                <div className={`bubble ${m.role}`}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {m.content}
                  </ReactMarkdown>
                </div>
                {m.tools && m.tools.length > 0 && (
                  <div style={{marginTop:6}}>
                    {m.tools.map((t, j) => (
                      <span key={j} className={`tool-chip ${t.status === "ok" ? "ok" : "err"}`}>
                        {t.status === "ok" ? "✓" : "✗"} {t.tool_name}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              {m.role === "user" && <div className="bubble-avatar" style={{background:"rgba(79,142,247,.25)"}}>👤</div>}
            </div>
          ))}
          {loading && (
            <div className="bubble-row assistant">
              <div className="bubble-avatar">🤖</div>
              <div className="bubble assistant"><div className="typing-dot"><span/><span/><span/></div></div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="chat-input-area">
          <div className="chat-input-wrapper">
            <textarea
              className="chat-input"
              rows={1}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={onKey}
              placeholder="Ask me to find products, add to cart, apply discount…"
            />
            <button className="chat-send" onClick={sendMessage} disabled={loading || !input.trim()} title="Send">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="19" x2="12" y2="5"></line>
                <polyline points="5 12 12 5 19 12"></polyline>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
