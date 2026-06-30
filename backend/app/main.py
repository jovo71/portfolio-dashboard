"""
Investment Portfolio Dashboard - FastAPI Backend
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os
import subprocess

from sqlalchemy import inspect, text

from app.database import engine, Base, SessionLocal
from app.models import SystemLog, Portfolio, Investment
from app.api import auth, investments, prices, dividends, costs, performance, system, portfolios
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

APP_DIR = os.getenv("APP_DIR", "/opt/portfolio-dashboard")


def _migrate_portfolios():
    """Voeg portfolio-ondersteuning toe aan een bestaande database.

    - voegt de kolom investments.portfolio_id toe als die ontbreekt;
    - zorgt voor een standaard-portfolio 'Hoofdportefeuille';
    - wijst losse beleggingen (zonder portfolio) aan dat portfolio toe.
    """
    insp = inspect(engine)
    cols = [c["name"] for c in insp.get_columns("investments")]
    if "portfolio_id" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE investments ADD COLUMN portfolio_id INTEGER"))
        logger.info("Migratie: kolom investments.portfolio_id toegevoegd")

    db = SessionLocal()
    try:
        default = db.query(Portfolio).order_by(Portfolio.id).first()
        if not default:
            default = Portfolio(name="Hoofdportefeuille")
            db.add(default)
            db.commit()
            db.refresh(default)
            logger.info("Migratie: standaard-portfolio 'Hoofdportefeuille' aangemaakt")
        orphans = (
            db.query(Investment)
            .filter(Investment.portfolio_id.is_(None))
            .update({Investment.portfolio_id: default.id})
        )
        if orphans:
            db.commit()
            logger.info(f"Migratie: {orphans} beleggingen toegewezen aan '{default.name}'")
    finally:
        db.close()


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
    _migrate_portfolios()
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
app.include_router(portfolios.router, prefix="/api/portfolios", tags=["Portfolio's"])
app.include_router(investments.router, prefix="/api/investments", tags=["Beleggingen"])
app.include_router(prices.router, prefix="/api/prices", tags=["Koersen"])
app.include_router(dividends.router, prefix="/api/dividends", tags=["Dividend"])
app.include_router(costs.router, prefix="/api/costs", tags=["Kosten"])
app.include_router(performance.router, prefix="/api/performance", tags=["Performance"])
app.include_router(system.router, prefix="/api/system", tags=["Systeem"])


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Portfolio Dashboard API"}
