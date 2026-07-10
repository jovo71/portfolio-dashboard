"""Categorie API endpoints (niveau boven Portfolio)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.auth import get_current_user
from app.models import Category, Portfolio
from app.schemas import CategoryCreate, CategoryResponse

router = APIRouter()


def _to_response(c: Category, db: Session) -> dict:
    count = db.query(Portfolio).filter(Portfolio.category_id == c.id).count()
    return {"id": c.id, "name": c.name, "created_at": c.created_at, "num_portfolios": count}


@router.get("/", response_model=List[CategoryResponse])
def list_categories(db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    """Alle categorieën met aantal portfolio's."""
    return [_to_response(c, db) for c in db.query(Category).order_by(Category.id).all()]


@router.post("/", response_model=CategoryResponse, status_code=201)
def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Maak een nieuwe categorie aan."""
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Naam mag niet leeg zijn")
    c = Category(name=name)
    db.add(c)
    db.commit()
    db.refresh(c)
    return _to_response(c, db)


@router.put("/{category_id}", response_model=CategoryResponse)
def rename_category(
    category_id: int,
    data: CategoryCreate,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Hernoem een categorie."""
    c = db.query(Category).filter(Category.id == category_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Categorie niet gevonden")
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Naam mag niet leeg zijn")
    c.name = name
    db.commit()
    db.refresh(c)
    return _to_response(c, db)


@router.delete("/{category_id}", status_code=204)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Verwijder een categorie (alleen als er geen portfolio's in zitten en niet de laatste)."""
    c = db.query(Category).filter(Category.id == category_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Categorie niet gevonden")
    if db.query(Category).count() <= 1:
        raise HTTPException(status_code=400, detail="De laatste categorie kan niet worden verwijderd")
    if db.query(Portfolio).filter(Portfolio.category_id == category_id).count() > 0:
        raise HTTPException(status_code=400, detail="Verplaats eerst de portfolio's uit deze categorie")
    db.delete(c)
    db.commit()
