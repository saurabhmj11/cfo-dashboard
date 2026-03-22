import sys
import os
import pytest
import shutil
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.database import get_db, Base
from app.models.db_models import User

# Mock DB
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

# --- Scenario: Sparse Data (Low Confidence) ---
SPARSE_CSV = """Date,Revenue,Expenses,Category
2023-01-01,10000,8000,Operations
2023-02-01,12000,8500,Marketing
2023-03-01,11000,9000,Operations
""" # Only 3 rows -> Low Density -> Penalty

def test_shadow_cfo_confidence_penalty():
    print("\n[TEST] Verifying Shadow CFO Confidence Protocols...")
    
    # Auth
    client.post("/auth/register", json={"username": "cfo_check", "email": "cfo@check.com", "password": "pass"})
    token = client.post("/auth/token", data={"username": "cfo_check", "password": "pass"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Upload Sparse Data
    files = {'file': ('sparse.csv', SPARSE_CSV, 'text/csv')}
    response = client.post("/api/v1/analyze", files=files, headers=headers)
    assert response.status_code == 200
    data = response.json()
    
    # 1. Verify Data Quality Penalty
    dq_score = data["data"]["financial_metrics"]["confidence_score"]
    print(f"   ℹ️ Data Quality Score: {dq_score}")
    assert dq_score < 1.0, "Start condition met: Data should be penalized for sparsity."
    
    # 2. Verify Detective Confidence Limit
    # Detective observations should be capped by dq_score
    detective = data["data"]["detective"]
    obs_confidences = [obs["confidence"] for obs in detective["observations"]]
    print(f"   ℹ️ Detective Confidences: {obs_confidences}")
    
    for conf in obs_confidences:
        assert conf <= dq_score, f"Violation: Detective confidence {conf} exceeds Data Trust {dq_score}"
        
    print("   ✅ Protocol 1 Validated: Truth Penalty Propagated.")
    
    # 3. Verify Forecasting Agent (Regression)
    forecast = data["data"]["forecast"]
    model_conf = forecast["model_confidence"]
    print(f"   ℹ️ Forecast Model Confidence: {model_conf}")
    
    # With only 3 points, Regression R2 might be perfect (if linear) or terrible. 
    # But specifically, our logic caps it: min(data_conf, r2)
    assert model_conf <= dq_score, "Violation: Forecast confidence exceeds Data Trust."
    
    print("   ✅ Protocol 2 Validated: Forecaster respects Data Trust.")

    print("[SUCCESS] Shadow CFO Logic Active.")

if __name__ == "__main__":
    test_shadow_cfo_confidence_penalty()
