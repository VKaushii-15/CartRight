from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.db import Base, engine
from app.routers import catalog, cart, checkout, tools, chat

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Conversational Checkout Agent — Phase 1")

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
