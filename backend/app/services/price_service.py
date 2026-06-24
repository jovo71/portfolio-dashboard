"""Koersophaling service via Yahoo Finance."""
import yfinance as yf
from datetime import datetime, time
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.models import Investment, PriceHistory, SystemLog
from app.database import SessionLocal

logger = logging.getLogger(__name__)

# Statistieken bijhouden
_stats = {
    "successful_updates": 0,
    "failed_updates": 0,
    "last_update": None,
}


def get_current_price(ticker: str) -> Optional[float]:
    """Haal actuele koers op voor een ticker via Yahoo Finance."""
    if not ticker:
        return None
    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info
        price = info.last_price
        if price and price > 0:
            return float(price)
        # Fallback: recent history
        hist = stock.history(period="2d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
        return None
    except Exception as e:
        logger.warning(f"Koers ophalen mislukt voor {ticker}: {e}")
        return None


def update_all_prices(db: Session) -> dict:
    """Update koersen voor alle beleggingen in de database."""
    investments = db.query(Investment).all()
    results = {"success": 0, "failed": 0, "skipped": 0}

    for inv in investments:
        if not inv.ticker:
            results["skipped"] += 1
            continue

        price = get_current_price(inv.ticker)
        if price:
            history = PriceHistory(
                investment_id=inv.id,
                date=datetime.utcnow(),
                price=price,
                currency=inv.currency,
            )
            db.add(history)
            results["success"] += 1
            logger.info(f"Koers bijgewerkt: {inv.name} ({inv.ticker}) = {price}")
        else:
            results["failed"] += 1
            logger.warning(f"Koers ophalen mislukt voor: {inv.name} ({inv.ticker})")

    db.commit()

    # Log resultaat
    log = SystemLog(
        event_type="price_update_success" if results["failed"] == 0 else "price_update_partial",
        message=f"Koersupdate: {results['success']} succesvol, {results['failed']} mislukt, {results['skipped']} overgeslagen",
        details=str(results),
    )
    db.add(log)
    db.commit()

    _stats["successful_updates"] += results["success"]
    _stats["failed_updates"] += results["failed"]
    _stats["last_update"] = datetime.utcnow()

    return results


def backfill_history(db: Session, investment, period: str = "1y") -> dict:
    """Haal historische dagkoersen op via Yahoo Finance en vul price_history aan.

    Bestaande dagen worden overgeslagen, zodat herhaald ophalen geen
    duplicaten oplevert. `period` is een yfinance-periode (bijv. 1mo, 3mo, 1y, max).
    """
    if not investment.ticker:
        return {"added": 0, "reason": "geen ticker"}

    try:
        hist = yf.Ticker(investment.ticker).history(period=period)
    except Exception as e:
        logger.warning(f"Historie ophalen mislukt voor {investment.ticker}: {e}")
        return {"added": 0, "reason": str(e)}

    if hist is None or hist.empty:
        return {"added": 0, "reason": "geen data"}

    existing = {
        p.date.date()
        for p in db.query(PriceHistory)
        .filter(PriceHistory.investment_id == investment.id)
        .all()
    }

    added = 0
    for idx, row in hist.iterrows():
        d = idx.to_pydatetime()
        if d.date() in existing:
            continue
        try:
            close = float(row["Close"])
        except (TypeError, ValueError):
            continue
        if close <= 0:
            continue
        db.add(PriceHistory(
            investment_id=investment.id,
            date=d,
            price=close,
            currency=investment.currency,
        ))
        existing.add(d.date())
        added += 1

    db.commit()
    logger.info(f"Backfill {investment.ticker}: {added} koersen toegevoegd ({period})")
    return {"added": added}


def get_stats() -> dict:
    """Geef update statistieken terug."""
    return _stats.copy()


def get_latest_price(db: Session, investment_id: int) -> Optional[PriceHistory]:
    """Geef de meest recente koers voor een belegging."""
    return (
        db.query(PriceHistory)
        .filter(PriceHistory.investment_id == investment_id)
        .order_by(PriceHistory.date.desc())
        .first()
    )


def get_previous_close(db: Session, investment_id: int, before: datetime) -> Optional[PriceHistory]:
    """Geef de laatste koers van vóór de kalenderdag van `before`.

    Wordt gebruikt voor het dagrendement: de meest recente koers van een
    eerdere dag dan de laatst bekende koers.
    """
    day_start = datetime.combine(before.date(), time.min)
    return (
        db.query(PriceHistory)
        .filter(PriceHistory.investment_id == investment_id)
        .filter(PriceHistory.date < day_start)
        .order_by(PriceHistory.date.desc())
        .first()
    )


def run_price_update():
    """Voer koersupdate uit (voor scheduler)."""
    db = SessionLocal()
    try:
        logger.info("Automatische koersupdate gestart")
        results = update_all_prices(db)
        logger.info(f"Koersupdate klaar: {results}")
    except Exception as e:
        logger.error(f"Koersupdate mislukt: {e}")
        db.rollback()
        _stats["failed_updates"] += 1
        try:
            log = SystemLog(
                event_type="price_update_error",
                message=f"Koersupdate fout: {str(e)}",
            )
            db.add(log)
            db.commit()
        except Exception:
            pass
    finally:
        db.close()
