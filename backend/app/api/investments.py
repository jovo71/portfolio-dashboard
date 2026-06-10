"""Beleggingen API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import csv
import io
from datetime import date

from app.database import get_db
from app.auth import get_current_user
from app.models import Investment
from app.schemas import InvestmentCreate, InvestmentUpdate, InvestmentResponse
from app.services.price_service import get_latest_price

router = APIRouter()


def enrich_investment(inv: Investment, db: Session) -> dict:
    """Voeg actuele koersdata toe aan belegging."""
    latest = get_latest_price(db, inv.id)
    current_price = latest.price if latest else None
    current_value = current_price * inv.quantity if current_price else None
    purchase_value = inv.average_purchase_price * inv.quantity
    
    total_return = (current_value - purchase_value) if current_value else None
    total_return_pct = (total_return / purchase_value * 100) if (total_return is not None and purchase_value > 0) else None

    return {
        **inv.__dict__,
        "current_price": current_price,
        "current_value": current_value,
        "total_return": total_return,
        "total_return_pct": total_return_pct,
    }


@router.get("/", response_model=List[InvestmentResponse])
def list_investments(db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    """Haal alle beleggingen op."""
    investments = db.query(Investment).all()
    return [enrich_investment(inv, db) for inv in investments]


@router.post("/", response_model=InvestmentResponse, status_code=201)
def create_investment(
    data: InvestmentCreate,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Voeg een nieuwe belegging toe."""
    inv = Investment(**data.model_dump())
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return enrich_investment(inv, db)


@router.get("/{investment_id}", response_model=InvestmentResponse)
def get_investment(
    investment_id: int,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Haal een specifieke belegging op."""
    inv = db.query(Investment).filter(Investment.id == investment_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Belegging niet gevonden")
    return enrich_investment(inv, db)


@router.put("/{investment_id}", response_model=InvestmentResponse)
def update_investment(
    investment_id: int,
    data: InvestmentUpdate,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Wijzig een belegging."""
    inv = db.query(Investment).filter(Investment.id == investment_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Belegging niet gevonden")
    
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(inv, field, value)
    
    db.commit()
    db.refresh(inv)
    return enrich_investment(inv, db)


@router.delete("/{investment_id}", status_code=204)
def delete_investment(
    investment_id: int,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Verwijder een belegging."""
    inv = db.query(Investment).filter(Investment.id == investment_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Belegging niet gevonden")
    db.delete(inv)
    db.commit()


@router.post("/import/csv")
def import_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Importeer beleggingen via CSV."""
    content = file.file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    
    imported = 0
    errors = []
    
    for i, row in enumerate(reader):
        try:
            inv = Investment(
                name=row.get("naam") or row.get("name", ""),
                isin=row.get("isin"),
                ticker=row.get("ticker"),
                broker=row.get("broker"),
                quantity=float(row.get("aantal") or row.get("quantity", 0)),
                average_purchase_price=float(row.get("aankoopprijs") or row.get("average_purchase_price", 0)),
                currency=row.get("valuta") or row.get("currency", "EUR"),
                purchase_date=date.fromisoformat(row["aankoopdatum"]) if row.get("aankoopdatum") else None,
                management_fee_percentage=float(row.get("beheerskosten") or row.get("management_fee_percentage", 0)),
            )
            db.add(inv)
            imported += 1
        except Exception as e:
            errors.append(f"Rij {i+2}: {str(e)}")
    
    db.commit()
    return {"imported": imported, "errors": errors}


@router.get("/export/csv")
def export_csv(db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    """Exporteer beleggingen als CSV."""
    investments = db.query(Investment).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["naam", "isin", "ticker", "broker", "aantal", "aankoopprijs", "valuta", "aankoopdatum", "beheerskosten"])
    
    for inv in investments:
        writer.writerow([
            inv.name, inv.isin, inv.ticker, inv.broker,
            inv.quantity, inv.average_purchase_price,
            inv.currency, inv.purchase_date, inv.management_fee_percentage,
        ])
    
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=beleggingen.csv"},
    )
