# 🛒 CartRight: Conversational Checkout Agent

**CartRight** is an intelligent, LLM-powered ecommerce checkout assistant featuring a robust business-logic gate layer and seamless Razorpay payment integration. 

Built for our hackathon submission, this project demonstrates a highly secure, reliable, and user-friendly way to shop, add products, apply discounts, and checkout—all through natural language.

---

## ✨ Features & Innovations

### 1. The Gate Layer (Core Innovation)
LLMs are prone to hallucinations. We built a robust validation layer that sits between the LLM and the backend. Every tool call is:
- **Whitelisted**: Only registered tools are permitted execution.
- **Schema-Validated**: Pydantic strictly enforces parameter constraints (e.g., maximum discount rules).
- **Business-Rule Gated**: Validates live inventory, stock requirements, and valid cart totals before executing.
- **Cleanly Rejected**: Instead of crashing or ignoring the LLM, the gate returns structured JSON explaining *why* a call failed, allowing the AI to organically course-correct and respond to the user.

### 2. Conversational Ecommerce
Users communicate with a Groq-powered LLM, which autonomously orchestrates:
- **Catalog Search**: Navigating thousands of products based on natural language queries.
- **Cart Management**: Precision adds/removes based on live stock.
- **Smart Promos**: Dynamic discount generation and application.

### 3. Real Payment Processing
Deeply integrated with the **Razorpay SDK** (Test Mode). The agent provisions secure sessions, sets up the order payload, verifies webhooks & signatures, and confirms payments instantly in the frontend.

---

## 🏗 Architecture Highlights

```text
┌─────────────────────────────────────────────────────────────┐
│                      USER (React Frontend)                  │
└────────────────────────┬────────────────────────────────────┘
                         │ 
                         ↓ 
         ┌───────────────────────────────┐
         │  /chat/{session_id} Endpoint  │
         └────────────┬──────────────────┘
                      │
                      ↓
         ┌───────────────────────────────┐
         │   Groq LLM (Tool-Calling)     │
         └────────────┬──────────────────┘
                      │
                      ↓
         ┌───────────────────────────────────────┐
         │      run_tool_call() Gate Layer       │
         │ ┌─────────────────────────────────┐   │
         │ │ 1. Whitelist Check              │   │
         │ │ 2. Schema Validation (Pydantic) │   │
         │ │ 3. Business Rule Execution      │   │
         │ │ 4. Clean Result/Rejection       │   │
         │ └─────────────────────────────────┘   │
         └────────────┬──────────────────────────┘
                      │
         ┌────────────┼────────────┬──────────────┬──────────┐
         ↓            ↓            ↓              ↓          ↓
     Search      AddToCart    Discount       Checkout    Upsell
     Catalog      (valid)      (gated)       (Razorpay)  (suggest)
         │            │            │              │          │
         └────────────┼────────────┴──────────────┴──────────┘
                      ↓
         ┌─────────────────────────────────┐
         │  PostgreSQL / SQLite Database   │
         │  • Products & Live Stock        │
         │  • Cart Sessions & Totals       │
         │  • Razorpay Orders              │
         │  • Message History              │
         └─────────────────────────────────┘
```

---

## 🚀 Quick Start — Local Development

### Prerequisites
1. Python 3.10+
2. Node.js & npm (for frontend)
3. A Razorpay Account (API Key Id & Secret for Test Mode)
4. A Groq API Key

### Backend Setup

```bash
# 1. Create a Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup environment variables defining API keys
export GROQ_API_KEY="your-groq-api-key"
export RAZORPAY_KEY_ID="your-razorpay-key"
export RAZORPAY_KEY_SECRET="your-razorpay-secret"
export DATABASE_URL="sqlite:///./cartright.db"

# 4. Seed database with catalog products & discount rules
python3 seed.py

# 5. Start the FastAPI backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install Node dependencies
npm install

# 3. Start the Vite React app
npm run dev
```
*The frontend runs on `http://localhost:5173`.*

---

## 🤖 Seeing It In Action

### Option 1: REST API Demo Script
We've included an end-to-end Python demo script that simulates the exact REST timeline (Search -> Add -> Discount -> Checkout) to demonstrate gating, independent of the LLM.

```bash
# Ensure backend is running, then in a new terminal:
python3 demo.py
```

### Option 2: The Conversational Chat
Interact with the frontend UI or run the integration chat demo locally:
```bash
python3 test_chat.py
```

---

## 🏆 Hackathon Submission Checklist (Judging Criteria)

1. **Practical Application**: ✅ E-commerce checkout process fully implemented with a sleek UI.
2. **AI Integration**: ✅ Uses Groq LLM tool-calling safely behind a strict rule gate.
3. **Guardrails & Security**: ✅ Discounts strictly capped (e.g. 20%), preventing hallucinated price drops. 
4. **Third-Party Integrations**: ✅ End-to-end Razorpay payment checkout built-in.
5. **State Awareness**: ✅ Session-based carts & chat history for memory context.

**Built with**: React, Vite, Python, FastAPI, SQLite/PostgreSQL, SQLAlchemy, Pydantic, Groq API, Razorpay SDK.
