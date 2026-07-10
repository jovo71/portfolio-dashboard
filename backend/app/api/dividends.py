"""Dividend API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.database import get_db
from app.auth import get_current_user
from app.models import Dividend, Investment, Portfolio
from app.schemas import DividendCreate, DividendResponse

router = APIRouter()


@router.get("/", response_model=List[DividendResponse])
def list_dividends(
    investment_id: int = None,
    portfolio_id: int = None,
    category_id: int = None,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    query = db.query(Dividend)
    if investment_id:
        query = query.filter(Dividend.investment_id == investment_id)
    if portfolio_id:
        query = query.join(Investment).filter(Investment.portfolio_id == portfolio_id)
    elif category_id:
        query = query.join(Investment).join(Portfolio).filter(Portfolio.category_id == category_id)
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
def dividend_summary(
    portfolio_id: int = None,
    category_id: int = None,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Totaal dividend per jaar en per belegging."""
    from sqlalchemy import extract

    def scoped(q):
        if portfolio_id:
            return q.join(Investment).filter(Investment.portfolio_id == portfolio_id)
        if category_id:
            return q.join(Investment).join(Portfolio).filter(Portfolio.category_id == category_id)
        return q

    yearly_q = scoped(db.query(
        extract("year", Dividend.payment_date).label("year"),
        func.sum(Dividend.total_amount).label("total"),
    ))
    total_q = scoped(db.query(func.sum(Dividend.total_amount)))

    yearly = yearly_q.group_by("year").order_by("year").all()
    total = total_q.scalar() or 0.0
    
    return {
        "total": total,
        "by_year": [{"year": int(y), "total": float(t)} for y, t in yearly],
    }
