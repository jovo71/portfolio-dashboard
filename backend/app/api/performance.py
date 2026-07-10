"""Performance API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.database import get_db
from app.auth import get_current_user
from app.services.performance_service import calculate_portfolio_performance, get_portfolio_history

router = APIRouter()


@router.get("/")
def get_performance(
    period: str = "ytd",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    portfolio_id: Optional[int] = None,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Bereken portfolio performance voor een periode."""
    return calculate_portfolio_performance(db, period, start_date, end_date, portfolio_id, category_id)


@router.get("/history")
def get_history(
    days: int = 365,
    portfolio_id: Optional[int] = None,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Historische portefeuillewaarde."""
    return get_portfolio_history(db, days, portfolio_id, category_id)
