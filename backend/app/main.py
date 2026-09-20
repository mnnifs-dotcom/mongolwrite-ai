from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import api_router
from app.core.config import settings
from app.engine.warmup import keep_warm_loop, warm_now

PUBLIC_HOST = "mongolwrite.com"
LEGACY_HOSTS = frozenset(
    {
        "mongolwrite-ai.fly.dev",
        "www.mongolwrite.com",
    }
)


class CanonicalHostMiddleware(BaseHTTPMiddleware):
    """Send legacy hosts to the public mongolwrite.com URL."""

    async def dispatch(self, request: Request, call_next):
        host = (request.headers.get("host") or "").split(":")[0].lower()
        if host in LEGACY_HOSTS:
            path = request.url.path or "/"
            query = f"?{request.url.query}" if request.url.query else ""
            return RedirectResponse(
                url=f"https://{PUBLIC_HOST}{path}{query}",
                status_code=301,
            )
        return await call_next(request)


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
    "https://mongolwrite.com",
    "https://www.mongolwrite.com",
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
if settings.app_env == "production":
    app.add_middleware(CanonicalHostMiddleware)
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
    # Next static export writes page.html; Starlette StaticFiles(html=True) does not
    # map /page → page.html, so register explicit page routes before the mount.
    _admin_html = _frontend / "admin.html"
    if _admin_html.is_file():

        @app.get("/admin")
        @app.get("/admin/")
        def admin_page() -> FileResponse:
            return FileResponse(_admin_html)

    _seo_html = _frontend / "ugiin-aldaga-shalgah.html"
    if _seo_html.is_file():

        @app.get("/ugiin-aldaga-shalgah")
        @app.get("/ugiin-aldaga-shalgah/")
        def ugiin_aldaga_shalgah_page() -> FileResponse:
            return FileResponse(_seo_html)

    _aldaga_html = _frontend / "aldaga-shalgah.html"
    if _aldaga_html.is_file():

        @app.get("/aldaga-shalgah")
        @app.get("/aldaga-shalgah/")
        def aldaga_shalgah_page() -> FileResponse:
            return FileResponse(_aldaga_html)

    _terms_html = _frontend / "uilchilgeenii-nokhtsol.html"
    if _terms_html.is_file():

        @app.get("/uilchilgeenii-nokhtsol")
        @app.get("/uilchilgeenii-nokhtsol/")
        def terms_page() -> FileResponse:
            return FileResponse(_terms_html)

    _report_html = _frontend / "aldaa-medegdeh.html"
    if _report_html.is_file():

        @app.get("/aldaa-medegdeh")
        @app.get("/aldaa-medegdeh/")
        def report_error_page() -> FileResponse:
            return FileResponse(_report_html)

    _tolbor_html = _frontend / "tolbor.html"
    if _tolbor_html.is_file():

        @app.get("/tolbor")
        @app.get("/tolbor/")
        def tolbor_page() -> FileResponse:
            return FileResponse(_tolbor_html)

    app.mount("/", StaticFiles(directory=_frontend, html=True), name="frontend")
