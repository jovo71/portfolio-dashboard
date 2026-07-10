"""Portfolio API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.auth import get_current_user
from app.models import Portfolio, Investment, Category
from app.schemas import PortfolioCreate, PortfolioUpdate, PortfolioResponse

router = APIRouter()


def _to_response(p: Portfolio, db: Session) -> dict:
    count = db.query(Investment).filter(Investment.portfolio_id == p.id).count()
    return {
        "id": p.id, "name": p.name, "category_id": p.category_id,
        "created_at": p.created_at, "num_investments": count,
    }


def _default_category_id(db: Session):
    c = db.query(Category).order_by(Category.id).first()
    return c.id if c else None


@router.get("/", response_model=List[PortfolioResponse])
def list_portfolios(
    category_id: int = None,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Alle portfolio's, optioneel gefilterd op categorie."""
    query = db.query(Portfolio)
    if category_id:
        query = query.filter(Portfolio.category_id == category_id)
    return [_to_response(p, db) for p in query.order_by(Portfolio.id).all()]


@router.post("/", response_model=PortfolioResponse, status_code=201)
def create_portfolio(
    data: PortfolioCreate,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Maak een nieuw portfolio aan binnen een categorie."""
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Naam mag niet leeg zijn")
    p = Portfolio(name=name, category_id=data.category_id or _default_category_id(db))
    db.add(p)
    db.commit()
    db.refresh(p)
    return _to_response(p, db)


@router.put("/{portfolio_id}", response_model=PortfolioResponse)
def update_portfolio(
    portfolio_id: int,
    data: PortfolioUpdate,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Hernoem een portfolio en/of verplaats het naar een andere categorie."""
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio niet gevonden")
    if data.name is not None:
        name = data.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Naam mag niet leeg zijn")
        p.name = name
    if data.category_id is not None:
        if not db.query(Category).filter(Category.id == data.category_id).first():
            raise HTTPException(status_code=404, detail="Categorie niet gevonden")
        p.category_id = data.category_id
    db.commit()
    db.refresh(p)
    return _to_response(p, db)


@router.delete("/{portfolio_id}", status_code=204)
def delete_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Verwijder een portfolio (alleen als het leeg is en niet het laatste)."""
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio niet gevonden")
    if db.query(Portfolio).count() <= 1:
        raise HTTPException(status_code=400, detail="Het laatste portfolio kan niet worden verwijderd")
    if db.query(Investment).filter(Investment.portfolio_id == portfolio_id).count() > 0:
        raise HTTPException(status_code=400, detail="Verwijder of verplaats eerst de beleggingen in dit portfolio")
    db.delete(p)
    db.commit()
