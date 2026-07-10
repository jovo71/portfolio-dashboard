"""Koersophaling service via Yahoo Finance en Northern Trust FGR.

Yahoo wordt rechtstreeks via het publieke chart-endpoint bevraagd. De
yfinance-library is bewust niet in gebruik: die spreekt endpoints aan die
Yahoo heeft afgeschermd (401/429), waardoor koersophalen volledig faalde.
Een browser-User-Agent is verplicht, anders volgt HTTP 429.
"""
import os
import re
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


# Yahoo Finance. Zonder browser-User-Agent antwoordt Yahoo met HTTP 429.
YAHOO_SEARCH_URL = "https://query1.finance.yahoo.com/v1/finance/search"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
YAHOO_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}
_symbol_cache: dict = {}


def _yahoo_chart(symbol: str, range_: str = "1d", interval: str = "1d") -> dict:
    """Haal het chart-resultaat voor een symbool op. Gooit bij fouten."""
    resp = requests.get(
        YAHOO_CHART_URL.format(symbol=symbol),
        params={"range": range_, "interval": interval},
        headers=YAHOO_HEADERS,
        timeout=20,
    )
    resp.raise_for_status()
    chart = (resp.json() or {}).get("chart") or {}
    if chart.get("error"):
        raise ValueError(chart["error"].get("description") or "Yahoo-fout")
    results = chart.get("result") or []
    if not results:
        raise ValueError("geen koersdata")
    return results[0]


def _chart_closes(result: dict):
    """Geef (timestamps, closes) uit een chart-resultaat."""
    timestamps = result.get("timestamp") or []
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    return timestamps, (quote.get("close") or [])


def resolve_yahoo_symbol(isin: str) -> Optional[str]:
    """Zoek het Yahoo-beurssymbool bij een ISIN."""
    key = isin.strip().upper()
    if key in _symbol_cache:
        return _symbol_cache[key]
    symbol = None
    try:
        resp = requests.get(
            YAHOO_SEARCH_URL,
            params={"q": key, "quotesCount": 5, "newsCount": 0},
            headers=YAHOO_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        for q in resp.json().get("quotes", []):
            if q.get("symbol"):
                symbol = q["symbol"]
                break
    except Exception as e:
        logger.warning(f"Yahoo symbool-lookup mislukt voor {key}: {e}")
    _symbol_cache[key] = symbol
    return symbol


def _resolve_yahoo(ticker: str) -> Optional[str]:
    """Geef het effectieve Yahoo-symbool voor een ingevoerde ticker of ISIN."""
    t = ticker.strip()
    if _ISIN_RE.match(t.upper()):
        return resolve_yahoo_symbol(t)
    return t

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

    # ISIN van een beursgenoteerd fonds -> via Yahoo naar een symbool
    symbol = _resolve_yahoo(ticker)
    if not symbol:
        return None

    try:
        result = _yahoo_chart(symbol, range_="5d", interval="1d")
        price = (result.get("meta") or {}).get("regularMarketPrice")
        if price and float(price) > 0:
            return float(price)
        # Fallback: laatste geldige slotkoers uit de reeks
        _, closes = _chart_closes(result)
        for close in reversed(closes):
            if close:
                return float(close)
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
    duplicaten oplevert. `period` is een Yahoo-range (bijv. 1mo, 3mo, 1y, max).
    """
    if not investment.ticker:
        return {"added": 0, "reason": "geen ticker"}

    if _is_nt_ticker(investment.ticker):
        return {"added": 0, "reason": "northern_trust_geen_historie"}

    symbol = _resolve_yahoo(investment.ticker)
    if not symbol:
        return {"added": 0, "reason": "isin_niet_gevonden"}

    try:
        result = _yahoo_chart(symbol, range_=period, interval="1d")
    except Exception as e:
        logger.warning(f"Historie ophalen mislukt voor {investment.ticker}: {e}")
        return {"added": 0, "reason": str(e)}

    timestamps, closes = _chart_closes(result)
    if not timestamps:
        return {"added": 0, "reason": "geen data"}

    existing = {
        p.date.date()
        for p in db.query(PriceHistory)
        .filter(PriceHistory.investment_id == investment.id)
        .all()
    }

    added = 0
    for ts, close in zip(timestamps, closes):
        if not close or float(close) <= 0:
            continue
        d = datetime.utcfromtimestamp(ts)
        if d.date() in existing:
            continue
        db.add(PriceHistory(
            investment_id=investment.id,
            date=d,
            price=float(close),
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
