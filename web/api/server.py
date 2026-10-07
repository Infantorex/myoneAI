"""FastAPI Web Server for myoneAI / Tamil JARVIS Local Dashboard (Phase 11).

Provides local REST APIs and serves static frontend assets strictly on 127.0.0.1.
Zero public network exposure.
"""

from contextlib import asynccontextmanager
import logging
from pathlib import Path
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from app.core.config import get_settings
from web.api.routes import api_router

logger = logging.getLogger("myoneAI.web.server")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for application startup and shutdown."""
    settings = get_settings()
    logger.info("Starting myoneAI Web Dashboard on %s:%d (auth=%s)", settings.web_host, settings.web_port, settings.web_auth_enabled)
    yield
    logger.info("myoneAI Web Dashboard shutting down.")


def create_app() -> FastAPI:
    """Create and configure the FastAPI dashboard application."""
    settings = get_settings()

    app = FastAPI(
        title="myoneAI - Tamil JARVIS Web Dashboard",
        description="Local Web Dashboard and Control API for myoneAI",
        version=settings.app_version,
        docs_url="/docs",
        redoc_url=None,
        lifespan=lifespan,
    )

    # 1. Restrict CORS to known local origins only (Never '*' for authenticated endpoints)
    allowed_origins = [
        f"http://127.0.0.1:{settings.web_port}",
        f"http://localhost:{settings.web_port}",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # 2. Custom Structured Exception Handlers (Prevent traceback leakage)
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": str(exc.detail),
                },
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = []
        for err in exc.errors():
            loc = " -> ".join([str(x) for x in err.get("loc", [])])
            errors.append(f"{loc}: {err.get('msg', 'Invalid input')}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed.",
                    "details": errors,
                },
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled server exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected server error occurred.",
                },
            },
        )

    # 3. Health check endpoint
    @app.get("/api/health", tags=["Health"])
    async def health_check() -> dict:
        return {
            "status": "ok",
            "app": settings.app_name,
            "version": settings.app_version,
        }

    # 4. Include all API sub-routers
    app.include_router(api_router)
    from web.cloud.api import cloud_router
    app.include_router(cloud_router)

    # 5. Serve Frontend Static Files
    if FRONTEND_DIR.exists():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
    else:
        logger.warning("Frontend directory '%s' does not exist.", FRONTEND_DIR)

    return app


app = create_app()


def start_server() -> None:
    """Run server from command line (python -m web.api.server)."""
    settings = get_settings()

    auth_state = "ENABLED" if settings.web_auth_enabled else "DISABLED (Development Only)"

    print("=" * 45)
    print("myoneAI Web Dashboard")
    print("=" * 45)
    print(f"\nServer:")
    print(f"http://{settings.web_host}:{settings.web_port}")
    print(f"\nAuthentication: {auth_state}\n")

    uvicorn.run(
        "web.api.server:app",
        host=settings.web_host,
        port=settings.web_port,
        log_level="info",
    )


if __name__ == "__main__":
    start_server()
