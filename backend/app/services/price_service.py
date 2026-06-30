"""Koersophaling service via Yahoo Finance en Northern Trust FGR."""
import os
import re
import yfinance as yf
import requests
from datetime import datetime, time
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.models import Investment, PriceHistory, SystemLog
from app.database import SessionLocal

logger = logging.getLogger(__name__)

# Northern Trust FGR — publieke NAV-API (gesleuteld op ISIN), gebruikt door
# fgrinvesting.com. Geeft alleen de actuele NAV, geen historische reeks.
NT_NAV_URL = os.getenv(
    "NT_NAV_URL",
    "https://wcv7zjj5dd.execute-api.us-east-1.amazonaws.com/production/fgr-nav-data-test",
)
_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
_nt_cache = {"data": None, "fetched": None}


def _get_nt_nav_data() -> dict:
    """Haal de NT NAV-data op (gecachet, 1 uur)."""
    now = datetime.utcnow()
    if _nt_cache["data"] is not None and _nt_cache["fetched"] and \
            (now - _nt_cache["fetched"]).total_seconds() < 3600:
        return _nt_cache["data"]
    try:
        resp = requests.get(NT_NAV_URL, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        _nt_cache["data"] = data
        _nt_cache["fetched"] = now
        return data
    except Exception as e:
        logger.warning(f"Northern Trust NAV ophalen mislukt: {e}")
        return _nt_cache["data"] or {}


def get_nt_price(isin: str) -> Optional[float]:
    """Geef de actuele NAV per aandeel voor een Northern Trust FGR-fonds (op ISIN)."""
    entry = _get_nt_nav_data().get(isin.strip().upper())
    if not entry:
        return None
    try:
        nav = float(entry.get("nav per share"))
        return nav if nav > 0 else None
    except (TypeError, ValueError):
        return None


def _is_nt_ticker(ticker: str) -> Optional[str]:
    """Geef het ISIN terug als de ticker een Northern Trust FGR-fonds aanduidt.

    Ondersteunt zowel een kaal ISIN (bijv. NL0011225305) als de expliciete
    'NT:<ISIN>'-notatie.
    """
    t = ticker.strip().upper()
    if t.startswith("NT:"):
        t = t[3:]
    if _ISIN_RE.match(t) and t in _get_nt_nav_data():
        return t
    return None

# Statistieken bijhouden
_stats = {
    "successful_updates": 0,
    "failed_updates": 0,
    "last_update": None,
}


def get_current_price(ticker: str) -> Optional[float]:
    """Haal actuele koers op voor een ticker (Northern Trust FGR of Yahoo Finance)."""
    if not ticker:
        return None

    # Northern Trust FGR-fonds? (kaal ISIN of 'NT:<ISIN>')
    nt_isin = _is_nt_ticker(ticker)
    if nt_isin:
        return get_nt_price(nt_isin)

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

    if _is_nt_ticker(investment.ticker):
        return {"added": 0, "reason": "northern_trust_geen_historie"}

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
