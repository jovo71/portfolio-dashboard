"""Pydantic schemas voor request/response validatie."""
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.models import CostType


# Auth
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Investment
class InvestmentBase(BaseModel):
    name: str
    isin: Optional[str] = None
    ticker: Optional[str] = None
    broker: Optional[str] = None
    quantity: float
    average_purchase_price: float
    currency: str = "EUR"
    purchase_date: Optional[date] = None
    management_fee_percentage: float = 0.0


class InvestmentCreate(InvestmentBase):
    pass


class InvestmentUpdate(BaseModel):
    name: Optional[str] = None
    isin: Optional[str] = None
    ticker: Optional[str] = None
    broker: Optional[str] = None
    quantity: Optional[float] = None
    average_purchase_price: Optional[float] = None
    currency: Optional[str] = None
    purchase_date: Optional[date] = None
    management_fee_percentage: Optional[float] = None


class InvestmentResponse(InvestmentBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    current_price: Optional[float] = None
    current_value: Optional[float] = None
    total_return: Optional[float] = None
    total_return_pct: Optional[float] = None
    day_change: Optional[float] = None
    day_change_pct: Optional[float] = None
    price_updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Price History
class PriceHistoryResponse(BaseModel):
    id: int
    investment_id: int
    date: datetime
    price: float
    currency: str

    class Config:
        from_attributes = True


# Dividend
class DividendBase(BaseModel):
    investment_id: int
    payment_date: date
    amount_per_share: float
    total_amount: float
    currency: str = "EUR"


class DividendCreate(DividendBase):
    pass


class DividendResponse(DividendBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Cost Entry
class CostEntryBase(BaseModel):
    investment_id: int
    cost_type: CostType
    amount: float
    date: date
    description: Optional[str] = None


class CostEntryCreate(CostEntryBase):
    pass


class CostEntryResponse(CostEntryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Performance
class PerformanceQuery(BaseModel):
    period: str = "ytd"  # today, week, month, ytd, since_purchase, custom
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class PerformanceSummary(BaseModel):
    total_value: float
    total_cost: float
    total_return: float
    total_return_pct: float
    price_return: float
    price_return_pct: float
    dividend_return: float
    dividend_return_pct: float
    total_costs: float
    net_return: float
    net_return_pct: float
    num_investments: int


# System Status
class SystemStatus(BaseModel):
    last_update: Optional[datetime] = None
    successful_updates: int
    failed_updates: int
    scheduler_running: bool
    api_status: str
