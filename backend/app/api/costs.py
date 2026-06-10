"""Kosten API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import List

from app.database import get_db
from app.auth import get_current_user
from app.models import CostEntry, Investment
from app.schemas import CostEntryCreate, CostEntryResponse

router = APIRouter()


@router.get("/", response_model=List[CostEntryResponse])
def list_costs(
    investment_id: int = None,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    query = db.query(CostEntry)
    if investment_id:
        query = query.filter(CostEntry.investment_id == investment_id)
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
def costs_summary(db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    """Kostenoverzicht per jaar, belegging en broker."""
    from datetime import date
    current_year = date.today().year

    costs_this_year = (
        db.query(func.sum(CostEntry.amount))
        .filter(extract("year", CostEntry.date) == current_year)
        .scalar() or 0.0
    )

    costs_total = db.query(func.sum(CostEntry.amount)).scalar() or 0.0

    by_investment = (
        db.query(
            CostEntry.investment_id,
            Investment.name,
            func.sum(CostEntry.amount).label("total"),
        )
        .join(Investment)
        .group_by(CostEntry.investment_id, Investment.name)
        .all()
    )

    by_broker = (
        db.query(
            Investment.broker,
            func.sum(CostEntry.amount).label("total"),
        )
        .join(CostEntry)
        .group_by(Investment.broker)
        .all()
    )

    by_type = (
        db.query(
            CostEntry.cost_type,
            func.sum(CostEntry.amount).label("total"),
        )
        .group_by(CostEntry.cost_type)
        .all()
    )

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
