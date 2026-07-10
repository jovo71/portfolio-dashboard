"""Kosten API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import List

from app.database import get_db
from app.auth import get_current_user
from app.models import CostEntry, Investment, Portfolio
from app.schemas import CostEntryCreate, CostEntryResponse

router = APIRouter()


@router.get("/", response_model=List[CostEntryResponse])
def list_costs(
    investment_id: int = None,
    portfolio_id: int = None,
    category_id: int = None,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    query = db.query(CostEntry)
    if investment_id:
        query = query.filter(CostEntry.investment_id == investment_id)
    if portfolio_id:
        query = query.join(Investment).filter(Investment.portfolio_id == portfolio_id)
    elif category_id:
        query = query.join(Investment).join(Portfolio).filter(Portfolio.category_id == category_id)
    return query.order_by(CostEntry.date.desc()).all()


@router.post("/", response_model=CostEntryResponse, status_code=201)
def create_cost(
    data: CostEntryCreate,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    cost = CostEntry(**data.model_dump())
    db.add(cost)
    db.commit()
    db.refresh(cost)
    return cost


@router.delete("/{cost_id}", status_code=204)
def delete_cost(
    cost_id: int,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    cost = db.query(CostEntry).filter(CostEntry.id == cost_id).first()
    if not cost:
        raise HTTPException(status_code=404, detail="Kostenpost niet gevonden")
    db.delete(cost)
    db.commit()


@router.get("/summary")
def costs_summary(
    portfolio_id: int = None,
    category_id: int = None,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Kostenoverzicht per jaar, belegging en broker."""
    from datetime import date
    current_year = date.today().year

    def scoped(q):
        if portfolio_id:
            return q.join(Investment).filter(Investment.portfolio_id == portfolio_id)
        if category_id:
            return q.join(Investment).join(Portfolio).filter(Portfolio.category_id == category_id)
        return q

    costs_this_year = (
        scoped(db.query(func.sum(CostEntry.amount)))
        .filter(extract("year", CostEntry.date) == current_year)
        .scalar() or 0.0
    )

    costs_total = scoped(db.query(func.sum(CostEntry.amount))).scalar() or 0.0

    def scope_joined(q):
        """Voor queries die Investment al gejoined hebben."""
        if portfolio_id:
            return q.filter(Investment.portfolio_id == portfolio_id)
        if category_id:
            return q.join(Portfolio).filter(Portfolio.category_id == category_id)
        return q

    by_investment_q = scope_joined(db.query(
        CostEntry.investment_id,
        Investment.name,
        func.sum(CostEntry.amount).label("total"),
    ).join(Investment))
    by_investment = by_investment_q.group_by(CostEntry.investment_id, Investment.name).all()

    by_broker_q = scope_joined(db.query(
        Investment.broker,
        func.sum(CostEntry.amount).label("total"),
    ).join(CostEntry))
    by_broker = by_broker_q.group_by(Investment.broker).all()

    by_type_q = scoped(db.query(
        CostEntry.cost_type,
        func.sum(CostEntry.amount).label("total"),
    ))
    by_type = by_type_q.group_by(CostEntry.cost_type).all()

    return {
        "this_year": costs_this_year,
        "total": costs_total,
        "by_investment": [
            {"id": inv_id, "name": name, "total": float(total)}
            for inv_id, name, total in by_investment
        ],
        "by_broker": [
            {"broker": broker or "Onbekend", "total": float(total)}
            for broker, total in by_broker
        ],
        "by_type": [
            {"type": str(ct), "total": float(total)}
            for ct, total in by_type
        ],
    }
