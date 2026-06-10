"""
Investment Portfolio Dashboard - FastAPI Backend
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.database import engine, Base
from app.api import auth, investments, prices, dividends, costs, performance, system
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting Portfolio Dashboard API")
    Base.metadata.create_all(bind=engine)
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
