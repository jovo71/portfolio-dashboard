"""Dividend API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.database import get_db
from app.auth import get_current_user
from app.models import Dividend
from app.schemas import DividendCreate, DividendResponse

router = APIRouter()


@router.get("/", response_model=List[DividendResponse])
def list_dividends(
    investment_id: int = None,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    query = db.query(Dividend)
    if investment_id:
        query = query.filter(Dividend.investment_id == investment_id)
    return query.order_by(Dividend.payment_date.desc()).all()


@router.post("/", response_model=DividendResponse, status_code=201)
def create_dividend(
    data: DividendCreate,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    div = Dividend(**data.model_dump())
    db.add(div)
    db.commit()
    db.refresh(div)
    return div


@router.delete("/{dividend_id}", status_code=204)
def delete_dividend(
    dividend_id: int,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    div = db.query(Dividend).filter(Dividend.id == dividend_id).first()
    if not div:
        raise HTTPException(status_code=404, detail="Dividend niet gevonden")
    db.delete(div)
    db.commit()


@router.get("/summary")
def dividend_summary(db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    """Totaal dividend per jaar en per belegging."""
    from sqlalchemy import extract
    
    yearly = (
        db.query(
            extract("year", Dividend.payment_date).label("year"),
            func.sum(Dividend.total_amount).label("total"),
        )
        .group_by("year")
        .order_by("year")
        .all()
    )
    
    total = db.query(func.sum(Dividend.total_amount)).scalar() or 0.0
    
    return {
        "total": total,
        "by_year": [{"year": int(y), "total": float(t)} for y, t in yearly],
    }
