"""Service voor performanceberekeningen."""
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Investment, PriceHistory, Dividend, CostEntry


def get_period_dates(period: str, start_date: Optional[date] = None, end_date: Optional[date] = None):
    """Bereken start- en einddatum op basis van periode."""
    today = date.today()

    if period == "today":
        return today, today
    elif period == "week":
        start = today - timedelta(days=today.weekday())
        return start, today
    elif period == "month":
        return today.replace(day=1), today
    elif period == "ytd":
        return today.replace(month=1, day=1), today
    elif period == "since_purchase":
        return None, today  # None = gebruik aankoopdatum per belegging
    elif period == "custom" and start_date and end_date:
        return start_date, end_date
    else:
        return today.replace(month=1, day=1), today


def get_price_at_date(db: Session, investment_id: int, target_date: date) -> Optional[float]:
    """Haal koers op voor een specifieke datum (of dichtst bij)."""
    target_dt = datetime.combine(target_date, datetime.min.time())
    
    result = (
        db.query(PriceHistory)
        .filter(
            PriceHistory.investment_id == investment_id,
            PriceHistory.date <= target_dt,
        )
        .order_by(PriceHistory.date.desc())
        .first()
    )
    return result.price if result else None


def calculate_portfolio_performance(
    db: Session,
    period: str = "ytd",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    """Bereken portfolio performance voor een periode."""
    period_start, period_end = get_period_dates(period, start_date, end_date)
    investments = db.query(Investment).all()

    total_current_value = 0.0
    total_purchase_value = 0.0
    total_start_value = 0.0
    total_dividend = 0.0
    total_costs = 0.0
    investment_details = []

    for inv in investments:
        # Huidige koers
        latest_price = (
            db.query(PriceHistory)
            .filter(PriceHistory.investment_id == inv.id)
            .order_by(PriceHistory.date.desc())
            .first()
        )
        current_price = latest_price.price if latest_price else inv.average_purchase_price
        current_value = current_price * inv.quantity

        # Aankoopwaarde
        purchase_value = inv.average_purchase_price * inv.quantity

        # Startwaarde voor de periode
        if period == "since_purchase" or period_start is None:
            start_value = purchase_value
        else:
            price_at_start = get_price_at_date(db, inv.id, period_start)
            start_value = (price_at_start or inv.average_purchase_price) * inv.quantity

        # Dividend in periode
        div_query = db.query(func.sum(Dividend.total_amount)).filter(
            Dividend.investment_id == inv.id
        )
        if period_start:
            div_query = div_query.filter(Dividend.payment_date >= period_start)
        if period_end:
            div_query = div_query.filter(Dividend.payment_date <= period_end)
        dividend = div_query.scalar() or 0.0

        # Kosten in periode
        cost_query = db.query(func.sum(CostEntry.amount)).filter(
            CostEntry.investment_id == inv.id
        )
        if period_start:
            cost_query = cost_query.filter(CostEntry.date >= period_start)
        if period_end:
            cost_query = cost_query.filter(CostEntry.date <= period_end)
        costs = cost_query.scalar() or 0.0

        price_return = current_value - start_value
        price_return_pct = (price_return / start_value * 100) if start_value > 0 else 0.0
        total_return = price_return + dividend - costs
        total_return_pct = (total_return / start_value * 100) if start_value > 0 else 0.0

        total_current_value += current_value
        total_purchase_value += purchase_value
        total_start_value += start_value
        total_dividend += dividend
        total_costs += costs

        investment_details.append({
            "id": inv.id,
            "name": inv.name,
            "ticker": inv.ticker,
            "broker": inv.broker,
            "quantity": inv.quantity,
            "current_price": current_price,
            "current_value": current_value,
            "purchase_value": purchase_value,
            "start_value": start_value,
            "price_return": price_return,
            "price_return_pct": price_return_pct,
            "dividend": dividend,
            "costs": costs,
            "total_return": total_return,
            "total_return_pct": total_return_pct,
            "weight": 0.0,  # berekend hierna
        })

    # Gewichten berekenen
    for detail in investment_details:
        detail["weight"] = (detail["current_value"] / total_current_value * 100) if total_current_value > 0 else 0.0

    price_return_total = total_current_value - total_start_value
    price_return_pct_total = (price_return_total / total_start_value * 100) if total_start_value > 0 else 0.0
    total_return_total = price_return_total + total_dividend - total_costs
    total_return_pct_total = (total_return_total / total_start_value * 100) if total_start_value > 0 else 0.0

    return {
        "period": period,
        "period_start": period_start.isoformat() if period_start else None,
        "period_end": period_end.isoformat() if period_end else None,
        "summary": {
            "total_value": total_current_value,
            "total_purchase_value": total_purchase_value,
            "total_start_value": total_start_value,
            "price_return": price_return_total,
            "price_return_pct": price_return_pct_total,
            "dividend_return": total_dividend,
            "dividend_return_pct": (total_dividend / total_start_value * 100) if total_start_value > 0 else 0.0,
            "total_costs": total_costs,
            "total_return": total_return_total,
            "total_return_pct": total_return_pct_total,
            "net_return": total_return_total,
            "net_return_pct": total_return_pct_total,
            "num_investments": len(investments),
        },
        "investments": investment_details,
    }


def get_portfolio_history(db: Session, days: int = 365) -> List[Dict]:
    """Geef historische portefeuillewaarde per dag."""
    investments = db.query(Investment).all()
    if not investments:
        return []

    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    # Verzamel alle datums met koersdata
    dates_with_data = (
        db.query(func.date(PriceHistory.date))
        .filter(PriceHistory.date >= datetime.combine(start_date, datetime.min.time()))
        .distinct()
        .order_by(func.date(PriceHistory.date))
        .all()
    )

    history = []
    for (day,) in dates_with_data:
        if isinstance(day, str):
            day = date.fromisoformat(day)
        total_value = 0.0
        for inv in investments:
            price = get_price_at_date(db, inv.id, day)
            if price:
                total_value += price * inv.quantity
        if total_value > 0:
            history.append({"date": day.isoformat(), "value": total_value})

    return history
