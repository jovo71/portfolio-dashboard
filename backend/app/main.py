"""
Investment Portfolio Dashboard - FastAPI Backend
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os
import subprocess

from app.database import engine, Base, SessionLocal
from app.models import SystemLog
from app.api import auth, investments, prices, dividends, costs, performance, system
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

APP_DIR = os.getenv("APP_DIR", "/opt/portfolio-dashboard")


def _log_deploy_completed():
    """Schrijf een 'deploy voltooid'-logregel als een deploy de marker achterliet."""
    marker = os.path.join(APP_DIR, "data", ".deploy_completed")
    if not os.path.exists(marker):
        return
    try:
        commit = subprocess.run(
            ["git", "-C", APP_DIR, "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip() or "onbekend"
    except (subprocess.SubprocessError, OSError):
        commit = "onbekend"

    db = SessionLocal()
    try:
        db.add(SystemLog(
            event_type="deploy_completed",
            message=f"Systeemupdate voltooid (nieuwe versie: {commit})",
        ))
        db.commit()
    finally:
        db.close()
    try:
        os.remove(marker)
    except OSError:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting Portfolio Dashboard API")
    Base.metadata.create_all(bind=engine)
    _log_deploy_completed()
    start_scheduler()
    yield
    stop_scheduler()
    logger.info("Portfolio Dashboard API stopped")


app = FastAPI(
    title="Investment Portfolio Dashboard",
    description="API voor het monitoren van beleggingsportefeuilles",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authenticatie"])
app.include_router(investments.router, prefix="/api/investments", tags=["Beleggingen"])
app.include_router(prices.router, prefix="/api/prices", tags=["Koersen"])
app.include_router(dividends.router, prefix="/api/dividends", tags=["Dividend"])
app.include_router(costs.router, prefix="/api/costs", tags=["Kosten"])
app.include_router(performance.router, prefix="/api/performance", tags=["Performance"])
app.include_router(system.router, prefix="/api/system", tags=["Systeem"])


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Portfolio Dashboard API"}
