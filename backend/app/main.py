from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.core.config import settings
from app.engine.runtime import get_engine


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
    engine = get_engine()
    engine.check("бэлэн")
    yield


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
    app.mount("/", StaticFiles(directory=_frontend, html=True), name="frontend")
