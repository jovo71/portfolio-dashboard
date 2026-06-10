"""Unit tests voor de Portfolio Dashboard API."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models import Investment
from datetime import date

TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


def get_token():
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "geheim123"})
    return resp.json()["access_token"]


def auth_headers():
    return {"Authorization": f"Bearer {get_token()}"}


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_login_success():
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "geheim123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_failure():
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "fout"})
    assert resp.status_code == 401


def test_investments_requires_auth():
    resp = client.get("/api/investments/")
    assert resp.status_code == 403


def test_create_investment():
    resp = client.post(
        "/api/investments/",
        json={
            "name": "VWRL ETF",
            "isin": "IE00B3RBWM25",
            "ticker": "VWRL.AS",
            "broker": "DeGiro",
            "quantity": 10.0,
            "average_purchase_price": 100.0,
            "currency": "EUR",
            "purchase_date": "2023-01-15",
            "management_fee_percentage": 0.22,
        },
        headers=auth_headers(),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "VWRL ETF"
    assert data["quantity"] == 10.0


def test_list_investments():
    client.post(
        "/api/investments/",
        json={"name": "Test ETF", "quantity": 5.0, "average_purchase_price": 50.0},
        headers=auth_headers(),
    )
    resp = client.get("/api/investments/", headers=auth_headers())
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_update_investment():
    create = client.post(
        "/api/investments/",
        json={"name": "Test ETF", "quantity": 5.0, "average_purchase_price": 50.0},
        headers=auth_headers(),
    )
    inv_id = create.json()["id"]
    
    resp = client.put(
        f"/api/investments/{inv_id}",
        json={"quantity": 10.0},
        headers=auth_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["quantity"] == 10.0


def test_delete_investment():
    create = client.post(
        "/api/investments/",
        json={"name": "Te verwijderen", "quantity": 1.0, "average_purchase_price": 10.0},
        headers=auth_headers(),
    )
    inv_id = create.json()["id"]
    
    resp = client.delete(f"/api/investments/{inv_id}", headers=auth_headers())
    assert resp.status_code == 204


def test_create_dividend():
    create = client.post(
        "/api/investments/",
        json={"name": "Dividend Aandeel", "quantity": 100.0, "average_purchase_price": 25.0},
        headers=auth_headers(),
    )
    inv_id = create.json()["id"]
    
    resp = client.post(
        "/api/dividends/",
        json={
            "investment_id": inv_id,
            "payment_date": "2024-03-15",
            "amount_per_share": 0.50,
            "total_amount": 50.0,
            "currency": "EUR",
        },
        headers=auth_headers(),
    )
    assert resp.status_code == 201
    assert resp.json()["total_amount"] == 50.0


def test_create_cost():
    create = client.post(
        "/api/investments/",
        json={"name": "ETF met kosten", "quantity": 50.0, "average_purchase_price": 80.0},
        headers=auth_headers(),
    )
    inv_id = create.json()["id"]
    
    resp = client.post(
        "/api/costs/",
        json={
            "investment_id": inv_id,
            "cost_type": "beheerskosten",
            "amount": 12.50,
            "date": "2024-01-31",
            "description": "Kwartaalkosten Q1",
        },
        headers=auth_headers(),
    )
    assert resp.status_code == 201
    assert resp.json()["amount"] == 12.50


def test_performance_endpoint():
    resp = client.get("/api/performance/?period=ytd", headers=auth_headers())
    assert resp.status_code == 200
    assert "summary" in resp.json()


def test_system_status():
    resp = client.get("/api/system/status", headers=auth_headers())
    assert resp.status_code == 200
    assert "scheduler_running" in resp.json()
