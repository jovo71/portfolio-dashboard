#!/usr/bin/env python3
"""
Voorbeelddata invulscript voor Portfolio Dashboard.
Gebruik: python seed_data.py

Dit script voegt realistische voorbeeldbeleggingen, dividend en kosten toe.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta
import random

# Database setup
os.environ.setdefault("DATABASE_URL", "sqlite:///./portfolio.db")

from app.database import engine, SessionLocal, Base
from app.models import Investment, PriceHistory, Dividend, CostEntry, CostType
from datetime import datetime

Base.metadata.create_all(bind=engine)
db = SessionLocal()

print("📊 Portfolio Dashboard — Voorbeelddata laden...")

# Bestaande data verwijderen
db.query(CostEntry).delete()
db.query(Dividend).delete()
db.query(PriceHistory).delete()
db.query(Investment).delete()
db.commit()

# Voorbeeldbeleggingen
INVESTMENTS = [
    {
        "name": "Vanguard FTSE All-World ETF",
        "isin": "IE00B3RBWM25",
        "ticker": "VWRL.AS",
        "broker": "DeGiro",
        "quantity": 25.0,
        "average_purchase_price": 98.50,
        "currency": "EUR",
        "purchase_date": date(2022, 3, 15),
        "management_fee_percentage": 0.22,
        "base_price": 115.0,
    },
    {
        "name": "iShares Core MSCI World ETF",
        "isin": "IE00B4L5Y983",
        "ticker": "IWDA.AS",
        "broker": "DeGiro",
        "quantity": 50.0,
        "average_purchase_price": 75.20,
        "currency": "EUR",
        "purchase_date": date(2021, 9, 1),
        "management_fee_percentage": 0.20,
        "base_price": 88.0,
    },
    {
        "name": "Royal Dutch Shell",
        "isin": "GB00BP6MXD84",
        "ticker": "SHEL.AS",
        "broker": "Rabobank",
        "quantity": 100.0,
        "average_purchase_price": 28.50,
        "currency": "EUR",
        "purchase_date": date(2020, 5, 10),
        "management_fee_percentage": 0.0,
        "base_price": 33.20,
    },
    {
        "name": "Unilever",
        "isin": "GB00B10RZP78",
        "ticker": "UNA.AS",
        "broker": "Rabobank",
        "quantity": 40.0,
        "average_purchase_price": 44.80,
        "currency": "EUR",
        "purchase_date": date(2021, 2, 20),
        "management_fee_percentage": 0.0,
        "base_price": 42.50,
    },
    {
        "name": "iShares MSCI Emerging Markets ETF",
        "isin": "IE00B0M63177",
        "ticker": "IEMA.AS",
        "broker": "DeGiro",
        "quantity": 30.0,
        "average_purchase_price": 30.10,
        "currency": "EUR",
        "purchase_date": date(2022, 11, 5),
        "management_fee_percentage": 0.18,
        "base_price": 27.80,
    },
]

investments = []
for data in INVESTMENTS:
    base_price = data.pop("base_price")
    inv = Investment(**data)
    db.add(inv)
    db.flush()
    investments.append((inv, base_price))
    print(f"  ✅ Belegging: {inv.name}")

# Historische koersen (365 dagen)
print("\n📈 Historische koersen genereren...")
today = date.today()
for inv, base_price in investments:
    price = base_price * 0.85
    for i in range(365, -1, -1):
        d = today - timedelta(days=i)
        if d.weekday() < 5:  # werkdagen
            change = random.gauss(0.0003, 0.012)
            price = max(price * (1 + change), 1.0)
            ph = PriceHistory(
                investment_id=inv.id,
                date=datetime.combine(d, datetime.min.time()),
                price=round(price, 4),
                currency=inv.currency,
            )
            db.add(ph)

# Dividend
print("\n💰 Dividend toevoegen...")
DIVIDENDS = [
    # VWRL — kwartaaldividend
    (0, "2023-03-20", 0.48, 12.00),
    (0, "2023-06-20", 0.52, 13.00),
    (0, "2023-09-20", 0.49, 12.25),
    (0, "2023-12-20", 0.55, 13.75),
    (0, "2024-03-20", 0.51, 12.75),
    # Shell — kwartaaldividend
    (2, "2023-03-25", 0.33, 33.00),
    (2, "2023-06-25", 0.33, 33.00),
    (2, "2023-09-25", 0.34, 34.00),
    (2, "2023-12-25", 0.35, 35.00),
    # Unilever — halfjaarlijks
    (3, "2023-05-17", 0.42, 16.80),
    (3, "2023-11-15", 0.43, 17.20),
]
for inv_idx, pay_date, per_share, total in DIVIDENDS:
    inv, _ = investments[inv_idx]
    div = Dividend(
        investment_id=inv.id,
        payment_date=date.fromisoformat(pay_date),
        amount_per_share=per_share,
        total_amount=total,
        currency="EUR",
    )
    db.add(div)

# Kosten
print("\n💸 Kosten toevoegen...")
COSTS = [
    (0, CostType.BEHEER, 5.40, "2023-12-31", "Beheerskosten 2023 Q4"),
    (1, CostType.BEHEER, 6.00, "2023-12-31", "Beheerskosten 2023 Q4"),
    (1, CostType.BEHEER, 6.00, "2024-03-31", "Beheerskosten 2024 Q1"),
    (2, CostType.TRANSACTIE, 2.50, "2023-05-10", "Aankoop Shell"),
    (3, CostType.TRANSACTIE, 2.50, "2021-02-20", "Aankoop Unilever"),
    (2, CostType.SERVICE, 8.00, "2023-12-31", "Servicekosten Rabobank 2023"),
    (3, CostType.SERVICE, 4.00, "2023-12-31", "Servicekosten Rabobank 2023"),
    (4, CostType.BEHEER, 4.00, "2023-12-31", "Beheerskosten Emerging Markets 2023"),
]
for inv_idx, cost_type, amount, dt, desc in COSTS:
    inv, _ = investments[inv_idx]
    c = CostEntry(
        investment_id=inv.id,
        cost_type=cost_type,
        amount=amount,
        date=date.fromisoformat(dt),
        description=desc,
    )
    db.add(c)

db.commit()
db.close()

print(f"""
✨ Voorbeelddata geladen!

  📊 {len(INVESTMENTS)} beleggingen
  📈 365 dagen koershistorie per belegging
  💰 {len(DIVIDENDS)} dividenduitbetalingen
  💸 {len(COSTS)} kostenposten

Start de applicatie en log in met:
  Gebruiker: admin
  Wachtwoord: geheim123
""")
