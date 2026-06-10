"""Koersen API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.auth import get_current_user
from app.models import PriceHistory
from app.schemas import PriceHistoryResponse
from app.services.price_service import update_all_prices, get_stats

router = APIRouter()


@router.post("/refresh")
def refresh_prices(db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    """Handmatige koersverversing."""
    results = update_all_prices(db)
    return {"message": "Koersen bijgewerkt", "results": results}


@router.get("/stats")
def get_price_stats(user: str = Depends(get_current_user)):
    """Statistieken over koersupdates."""
    return get_stats()


@router.get("/{investment_id}/history", response_model=List[PriceHistoryResponse])
def get_price_history(
    investment_id: int,
    limit: int = 365,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Historische koersen voor een belegging."""
    return (
        db.query(PriceHistory)
        .filter(PriceHistory.investment_id == investment_id)
        .order_by(PriceHistory.date.desc())
        .limit(limit)
        .all()
    )
