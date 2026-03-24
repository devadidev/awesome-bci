"""
Energy Geopolitics Intelligence Platform - FastAPI Application Entry Point
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from src.config import get_settings
from src.logger import configure_logging, get_logger
from src.data.seed import load_seed_data
from src.recovery import RecoveryManager
from src.collectors import PriceCollector, NewsCollector, SanctionsCollector
from src.api.routes import events, assets, intelligence, health

logger = get_logger(__name__)
settings = get_settings()

# Global collector instances
_collectors = []
_recovery_manager: RecoveryManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    global _collectors, _recovery_manager

    configure_logging(settings.app_log_level)
    logger.info("startup", env=settings.app_env)

    # Load seed data
    if settings.load_seed_data:
        load_seed_data()

    # Initialize recovery manager
    _recovery_manager = RecoveryManager(
        checkpoint_dir=settings.checkpoint_dir,
        failure_threshold=settings.circuit_breaker_failure_threshold,
        recovery_timeout=float(settings.circuit_breaker_recovery_timeout),
        retry_max_attempts=settings.retry_max_attempts,
        retry_base_delay=settings.retry_base_delay,
    )

    # Register recovery manager with health routes
    health.set_recovery_manager(_recovery_manager)

    # Initialize and start collectors
    price_collector = PriceCollector(
        recovery_manager=_recovery_manager,
        eia_api_key=settings.eia_api_key,
        interval_seconds=60,
    )
    news_collector = NewsCollector(
        recovery_manager=_recovery_manager,
        news_api_key=settings.news_api_key,
        interval_seconds=300,
    )
    sanctions_collector = SanctionsCollector(
        recovery_manager=_recovery_manager,
        interval_seconds=3600,
    )

    _collectors = [price_collector, news_collector, sanctions_collector]

    # Run collectors once on startup to populate data
    for collector in _collectors:
        try:
            await collector.run_once()
        except Exception as exc:
            logger.warning("startup_collector_failed", collector=collector.collector_id, error=str(exc))

    # Start background collection loops
    for collector in _collectors:
        await collector.start()

    # Run initial alert scan
    from src.analysis.alert_engine import AlertEngine
    AlertEngine().run_full_scan()

    logger.info("startup_complete", collectors=len(_collectors))
    yield

    # Shutdown
    logger.info("shutdown")
    for collector in _collectors:
        await collector.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Energy Geopolitics Intelligence Platform",
        description=(
            "Real-time intelligence platform for oil & gas geopolitical risk assessment. "
            "Tracks events, assets, sanctions, and supply disruptions with a resilient "
            "recovery stack (circuit breakers, retries, checkpointing)."
        ),
        version="1.0.0-mvp",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    app.include_router(events.router, prefix="/api/v1")
    app.include_router(assets.router, prefix="/api/v1")
    app.include_router(intelligence.router, prefix="/api/v1")
    app.include_router(health.router, prefix="/api/v1")

    # Serve dashboard static files
    dashboard_dir = os.path.join(os.path.dirname(__file__), "..", "dashboard")
    if os.path.exists(dashboard_dir):
        app.mount("/static", StaticFiles(directory=dashboard_dir), name="static")

        @app.get("/")
        async def serve_dashboard():
            return FileResponse(os.path.join(dashboard_dir, "index.html"))

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
        log_level=settings.app_log_level.lower(),
    )
