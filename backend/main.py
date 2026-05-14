import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from routes.auth import router as auth_router
from routes.calendar import router as calendar_router
from routes.chat import router as chat_router
from routes.gmail import router as gmail_router
from routes.voice import router as voice_router

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Backend starting up — all routers registered.")
    yield
    print("Backend shutting down.")


app = FastAPI(
    title="AI Assistant API",
    version="0.4.0",
    lifespan=lifespan,
    # Hide docs in production to avoid leaking route details
    docs_url="/api/docs" if os.getenv("APP_ENV") != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    # In production the frontend is same-origin; keep localhost for local dev
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routers (registered first so they take priority over static mount) ────
app.include_router(auth_router)
app.include_router(calendar_router)
app.include_router(chat_router)
app.include_router(gmail_router)
app.include_router(voice_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.4.0"}


# ── Serve built React app (production) ───────────────────────────────────────
# Vite outputs to backend/static/ (see frontend/vite.config.js).
# In dev the Vite dev server (port 5173) serves the frontend instead.

_index = STATIC_DIR / "index.html"
_assets = STATIC_DIR / "assets"

if _assets.exists():
    # Serve hashed JS/CSS bundles — long cache headers are fine here
    app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

if _index.exists():
    # SPA fallback: any route not matched by an API router returns index.html
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        # Serve real files that live at the static root (favicon, manifest, etc.)
        candidate = STATIC_DIR / full_path
        if candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(_index))
else:
    @app.get("/{full_path:path}", include_in_schema=False)
    async def dev_notice(full_path: str):
        return JSONResponse(
            {"info": "Frontend not built yet. Run build.sh or start the Vite dev server."},
            status_code=200,
        )
