import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import health, ops, scan, shares

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)


def create_app() -> FastAPI:
    app = FastAPI(title="LibCloud")

    origins = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
    ]
    if settings.frontend_url:
        origins.append(settings.frontend_url)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(scan.router)
    app.include_router(shares.router)
    app.include_router(health.router)
    app.include_router(ops.router)

    @app.middleware("http")
    async def ops_noindex(request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path == "/ops" or path.startswith(("/ops/", "/api/ops")):
            response.headers["X-Robots-Tag"] = "noindex, nofollow"
            response.headers.setdefault("Cache-Control", "no-store")
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
            )
        return response

    return app


app = create_app()
