import React, { useEffect, useRef, useState } from "react";
import { genSessionId } from "../utils/session";
import { sendChatMessage } from "../api/client";

export default function ChatAssistant() {
  const [sessionId] = useState(genSessionId);
  const [messages, setMessages] = useState([
    { role: "assistant", content: "Hi! I'm your shopping assistant 🛍️\nTell me what you're looking for — I can search products, add items to your cart, apply discounts, and checkout for you!" }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  async function sendMessage() {
    const text = input.trim();
    if (!text || loading) return;
    setMessages(m => [...m, { role: "user", content: text }]);
    setInput("");
    setLoading(true);
    try {
      const data = await sendChatMessage(sessionId, text);
      const reply = data.assistant_message || "Done!";
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
                <div className={`bubble ${m.role}`}>{m.content}</div>
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
          <textarea
            className="chat-input"
            rows={1}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={onKey}
            placeholder="Ask me to find products, add to cart, apply discount…"
          />
          <button className="chat-send" onClick={sendMessage} disabled={loading || !input.trim()} title="Send">
            ➤
          </button>
        </div>
      </div>
    </div>
  );
}
