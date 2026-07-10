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
from app.models import SystemLog, Portfolio, Investment, Category
from app.api import auth, investments, prices, dividends, costs, performance, system, portfolios, categories
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

APP_DIR = os.getenv("APP_DIR", "/opt/portfolio-dashboard")


def _add_column_if_missing(table: str, column: str, ddl_type: str):
    """Voeg een kolom toe aan een bestaande tabel als die nog ontbreekt."""
    cols = [c["name"] for c in inspect(engine).get_columns(table)]
    if column not in cols:
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))
        logger.info(f"Migratie: kolom {table}.{column} toegevoegd")


def _migrate_schema():
    """Breng een bestaande database op het huidige schema.

    Belangrijk: alle ALTER TABLE's gebeuren vóór de eerste ORM-query, anders
    selecteert SQLAlchemy kolommen die nog niet bestaan.
    """
    _add_column_if_missing("investments", "portfolio_id", "INTEGER")
    _add_column_if_missing("portfolios", "category_id", "INTEGER")


def _migrate_data():
    """Vul de nieuwe structuur met zinnige standaardwaarden.

    - categorieën 'Beleggingen' en 'Pensioen' als er nog geen zijn;
    - een standaard-portfolio 'Hoofdportefeuille' als er nog geen is;
    - portfolio's zonder categorie: naam met 'giro' -> Pensioen, rest -> Beleggingen;
    - beleggingen zonder portfolio -> het eerste portfolio.
    Alles is achteraf aan te passen in de app.
    """
    db = SessionLocal()
    try:
        if db.query(Category).count() == 0:
            db.add_all([Category(name="Beleggingen"), Category(name="Pensioen")])
            db.commit()
            logger.info("Migratie: categorieën 'Beleggingen' en 'Pensioen' aangemaakt")

        beleggingen = db.query(Category).filter(Category.name == "Beleggingen").first()
        pensioen = db.query(Category).filter(Category.name == "Pensioen").first()
        fallback_cat = beleggingen or db.query(Category).order_by(Category.id).first()

        # Standaard-portfolio als er nog geen enkel portfolio bestaat
        default_pf = db.query(Portfolio).order_by(Portfolio.id).first()
        if not default_pf:
            default_pf = Portfolio(
                name="Hoofdportefeuille",
                category_id=fallback_cat.id if fallback_cat else None,
            )
            db.add(default_pf)
            db.commit()
            db.refresh(default_pf)
            logger.info("Migratie: standaard-portfolio 'Hoofdportefeuille' aangemaakt")

        # Portfolio's zonder categorie
        pf_orphans = db.query(Portfolio).filter(Portfolio.category_id.is_(None)).all()
        for p in pf_orphans:
            is_giro = "giro" in (p.name or "").lower()
            p.category_id = pensioen.id if (is_giro and pensioen) else (fallback_cat.id if fallback_cat else None)
        if pf_orphans:
            db.commit()
            logger.info(f"Migratie: {len(pf_orphans)} portfolio's aan een categorie toegewezen")

        # Beleggingen zonder portfolio
        inv_orphans = (
            db.query(Investment)
            .filter(Investment.portfolio_id.is_(None))
            .update({Investment.portfolio_id: default_pf.id})
        )
        if inv_orphans:
            db.commit()
            logger.info(f"Migratie: {inv_orphans} beleggingen toegewezen aan '{default_pf.name}'")
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
    _migrate_schema()
    _migrate_data()
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
app.include_router(categories.router, prefix="/api/categories", tags=["Categorieën"])
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
