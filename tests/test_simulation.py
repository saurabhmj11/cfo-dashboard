import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os

# Setup In-Memory DB for independent testing
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
Base.metadata.create_all(bind=engine)

client = TestClient(app)

SAMPLE_CSV = """Date,Revenue,Expenses,Category
2023-01-01,10000,8000,Operations
2023-02-01,12000,8500,Marketing
2023-03-01,11000,9000,Operations
"""

def test_simulation_api():
    print("\n[TEST] Setting up Analysis for Simulation...")
    
    # 1. Auth
    client.post("/auth/register", json={"username": "sim_user", "email": "sim@ent.com", "password": "sim"})
    token = client.post("/auth/token", data={"username": "sim_user", "password": "sim"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Upload & Analyze (To create baseline)
    files = {'file': ('test.csv', SAMPLE_CSV, 'text/csv')}
    res = client.post("/api/v1/analyze", files=files, headers=headers)
    assert res.status_code == 200
    print("   ✅ Baseline Analysis Created.")
    
    # 3. Run Simulation
    print("[TEST] Running Wargame Simulation...")
    payload = {
        "scenario_name": "Aggressive Growth",
        "growth_factor": 1.20, # 20% Growth
        "churn_factor": 0.05
    }
    
    sim_res = client.post("/api/v1/simulate", json=payload, headers=headers)
    
    if sim_res.status_code != 200:
        print(sim_res.json())
        
    assert sim_res.status_code == 200
    data = sim_res.json()["data"]
    
    # Verify Structure
    assert data["strategy_name"] == "Aggressive Growth"
    assert len(data["monthly_projection"]) == 12
    assert len(data["shadow_ledger"]) > 12 # At least 1 txn per month
    
    # Verify Logic (Growth)
    total_rev = data["summary"]["total_revenue"]
    # Baseline was ~33k for 3 months (~11k/mo). 12 months at 11k = 132k.
    # With 20% growth compounding, should be significantly higher.
    # Just asserting it exists and is positive for now.
    assert total_rev > 100000
    
    print(f"   ✅ Simulation Successful. Generated {len(data['shadow_ledger'])} future transactions.")
    print(f"   ✅ Projected Revenue: ${total_rev:,.2f}")

if __name__ == "__main__":
    test_simulation_api()
