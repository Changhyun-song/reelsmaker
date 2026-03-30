from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from shared.config import get_settings, setup_logging
from shared.database import async_session_factory
from app.api.router import api_router
from app.seed import run_all_seeds

settings = get_settings()
logger = setup_logging("reelsmaker.api")


class FixRedirectMiddleware(BaseHTTPMiddleware):
    """Rewrite absolute Location headers to relative paths.

    When running behind a reverse proxy (e.g. Next.js rewrite),
    FastAPI's redirect_slashes produces Location headers with the
    internal hostname (e.g. http://api:8000/...). This middleware
    strips the scheme+host so browsers only see a relative path.
    """

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        location = response.headers.get("location")
        if location and response.status_code in (301, 302, 307, 308):
            parsed = urlparse(location)
            if parsed.scheme and parsed.netloc:
                relative = parsed._replace(scheme="", netloc="").geturl()
                response.headers["location"] = relative
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("API starting — debug=%s log_level=%s", settings.debug, settings.log_level)
    if settings.auto_seed:
        async with async_session_factory() as session:
            await run_all_seeds(session)
    logger.info("API ready")
    yield
    logger.info("API shutting down")


app = FastAPI(
    title="ReelsMaker API",
    description="High-quality AI video production pipeline",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(FixRedirectMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
