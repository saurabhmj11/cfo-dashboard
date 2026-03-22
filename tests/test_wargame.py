from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, Base, engine
from app.models.db_models import User, Dataset, AnalysisRun
from app.services.auth_service import create_access_token
import sqlalchemy
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import pytest

# Setup Test DB
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture
def auth_header():
    # Create Mock User
    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == "test_general").first()
    if not user:
        user = User(username="test_general", email="general@test.com", hashed_password="fake")
        db.add(user)
        db.commit()
    
    token = create_access_token(data={"sub": user.username})
    return {"Authorization": f"Bearer {token}"}

def test_wargame_simulation(auth_header):
    # 1. Setup: Ensure we have at least one AnalysisRun to base the sim on
    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == "test_general").first()
    
    # Mock Run Data
    mock_financials = {
        "monthly_data": [
            {"month": "2023-12", "revenue": 10000, "expenses": 5000, "net_profit": 5000, "margin_percent": 50.0}
        ],
        "summary_revenue": 10000,
        "summary_expenses": 5000,
        "summary_profit": 5000,
        "avg_margin": 50.0
    }
    
    run = AnalysisRun(
        user_id=user.id,
        dataset_id=1, # Mock
        metrics_result={"financials": mock_financials},
        forecast_result={},
        advisor_result={},
        run_date=datetime.now()
    )
    db.add(run)
    db.commit()
    
    # 2. Act: Run Simulation via API
    payload = {
        "scenario_name": "Aggressive Growth",
        "growth_factor": 1.5, # 50% Growth
        "churn_factor": 0.0
    }
    
    response = client.post("/api/v1/simulate", json=payload, headers=auth_header)
    
    # 3. Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    
    sim_data = data["data"]
    assert len(sim_data["monthly_projection"]) == 12 # 12 months simulated
    
    # Check if growth happened (Result Revenue > Baseline 10000 * 12)
    total_revenue = sim_data["summary"]["total_revenue"]
    assert total_revenue > 120000 # Should be significantly higher due to 50% growth
    
    print(f"\nSimulation Result: Revenue {total_revenue} (Baseline ~120k)")
