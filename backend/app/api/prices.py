"""Koersen API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.auth import get_current_user
from app.models import PriceHistory, Investment
from app.schemas import PriceHistoryResponse
from app.services.price_service import update_all_prices, get_stats, backfill_history

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


@router.post("/{investment_id}/backfill")
def backfill_prices(
    investment_id: int,
    period: str = "1y",
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Haal historische koersen op via Yahoo Finance voor een belegging."""
    inv = db.query(Investment).filter(Investment.id == investment_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Belegging niet gevonden")
    return backfill_history(db, inv, period)


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
