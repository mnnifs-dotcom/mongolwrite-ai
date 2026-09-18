from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.core.config import settings
from app.engine.warmup import keep_warm_loop, warm_now


def _frontend_dir() -> Path | None:
    env = settings.frontend_dir.strip()
    if env:
        path = Path(env)
        return path if (path / "index.html").is_file() else None
    if settings.app_env == "production":
        path = Path(__file__).resolve().parents[2] / "frontend" / "out"
        if (path / "index.html").is_file():
            return path
    return None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    import asyncio

    # Load Hunspell and run sample checks before traffic — no admin button needed.
    await asyncio.to_thread(warm_now)
    stop = asyncio.Event()
    task = asyncio.create_task(keep_warm_loop(stop))
    try:
        yield
    finally:
        stop.set()
        await task


app = FastAPI(title="MongolWrite AI", version="0.1.0", lifespan=lifespan)
_frontend = _frontend_dir()
_origins = {
    settings.frontend_origin,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
}
_allow_all = settings.app_env == "production"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_all else sorted(_origins),
    allow_origin_regex=None
    if _allow_all
    else r"http://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+)(:\d+)?",
    allow_credentials=not _allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)

if _frontend is None:

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "name": "MongolWrite AI",
            "status": "ok",
            "app": settings.frontend_origin,
            "docs": "/docs",
            "health": "/health",
        }

else:
    # Next static export writes admin.html; Starlette StaticFiles(html=True) does not
    # map /admin → admin.html, so register an explicit page route before the mount.
    _admin_html = _frontend / "admin.html"
    if _admin_html.is_file():

        @app.get("/admin")
        @app.get("/admin/")
        def admin_page() -> FileResponse:
            return FileResponse(_admin_html)

    app.mount("/", StaticFiles(directory=_frontend, html=True), name="frontend")
