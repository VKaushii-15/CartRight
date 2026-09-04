from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from contextlib import asynccontextmanager

from app.db import Base, engine, SessionLocal
from app.routers import catalog, cart, checkout, tools, chat
from app.models import Cart, CartItem, Order, ChatMessage, PendingToolCall, DiscountCode

Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager to wipe session data on server restart."""
    db = SessionLocal()
    try:
        db.query(PendingToolCall).delete()
        db.query(ChatMessage).delete()
        db.query(Order).delete()
        db.query(CartItem).delete()
        db.query(Cart).delete()
        # Reset discount codes to unused
        db.query(DiscountCode).update({"is_used": False})
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to clear old sessions: {e}")
    finally:
        db.close()
        
    # Also clear in-memory chatbot state
    try:
        from app.groq_client import _conversation_states
        _conversation_states.clear()
    except ImportError:
        pass
        
    yield

app = FastAPI(title="Conversational Checkout Agent — Phase 1", lifespan=lifespan)

app.include_router(catalog.router)
app.include_router(cart.router)
app.include_router(checkout.router)
app.include_router(tools.router)
app.include_router(chat.router)

# If a built frontend exists, serve it as static files (for Replit / single-host deploy)
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.isdir(FRONTEND_DIST):
    app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIST)), name="static")


@app.get("/")
def root():
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "ok", "phase": 1}
