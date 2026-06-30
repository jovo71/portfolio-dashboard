"""SQLAlchemy database modellen."""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class CostType(str, enum.Enum):
    BEHEER = "beheerskosten"
    SERVICE = "servicekosten"
    TRANSACTIE = "transactiekosten"
    BEWAAR = "bewaarkosten"
    OVERIG = "overige kosten"


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    investments = relationship("Investment", back_populates="portfolio")


class Investment(Base):
    __tablename__ = "investments"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), index=True)
    name = Column(String, nullable=False)
    isin = Column(String, index=True)
    ticker = Column(String, index=True)
    broker = Column(String)  # Rabobank, DeGiro
    quantity = Column(Float, nullable=False)
    average_purchase_price = Column(Float, nullable=False)
    currency = Column(String, default="EUR")
    purchase_date = Column(Date)
    management_fee_percentage = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    portfolio = relationship("Portfolio", back_populates="investments")
    price_history = relationship("PriceHistory", back_populates="investment", cascade="all, delete-orphan")
    dividends = relationship("Dividend", back_populates="investment", cascade="all, delete-orphan")
    cost_entries = relationship("CostEntry", back_populates="investment", cascade="all, delete-orphan")


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    investment_id = Column(Integer, ForeignKey("investments.id"), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    price = Column(Float, nullable=False)
    currency = Column(String, default="EUR")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    investment = relationship("Investment", back_populates="price_history")


class Dividend(Base):
    __tablename__ = "dividends"

    id = Column(Integer, primary_key=True, index=True)
    investment_id = Column(Integer, ForeignKey("investments.id"), nullable=False)
    payment_date = Column(Date, nullable=False)
    amount_per_share = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    currency = Column(String, default="EUR")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    investment = relationship("Investment", back_populates="dividends")


class CostEntry(Base):
    __tablename__ = "cost_entries"

    id = Column(Integer, primary_key=True, index=True)
    investment_id = Column(Integer, ForeignKey("investments.id"), nullable=False)
    cost_type = Column(Enum(CostType), nullable=False)
    amount = Column(Float, nullable=False)
    date = Column(Date, nullable=False)
    description = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    investment = relationship("Investment", back_populates="cost_entries")


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    event_type = Column(String)  # price_update_success, price_update_error
    message = Column(String)
    details = Column(String)
