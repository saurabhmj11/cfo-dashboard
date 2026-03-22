from fastapi.testclient import TestClient
from app.main import app
import os

client = TestClient(app)

def test_analyze_needs_auth():
    print("Testing Analyze Endpoint Security...")
    # Create a dummy csv
    with open("test_dummy.csv", "w") as f:
        f.write("date,revenue,expenses,category\n2023-01-01,1000,500,Test\n2023-02-01,1200,600,Test")
    
    try:
        # 1. Access without token
        pass_without_token = False
        with open("test_dummy.csv", "rb") as f:
            response = client.post("/api/v1/analyze", files={"file": f})
        
        if response.status_code == 401:
            print("SUCCESS: Unauthorized access correctly rejected (401).")
            pass_without_token = True
        else:
            print(f"FAILURE: Expected 401, got {response.status_code}")
            
        assert pass_without_token

        # 2. Access with token
        # Login (assuming testuser_auth existing from previous test)
        # If not, let's register a new one just in case
        client.post("/auth/register", json={
            "username": "testuser_analysis",
            "email": "analysis@example.com",
            "password": "pass"
        })
        
        auth_response = client.post("/auth/token", data={"username": "testuser_analysis", "password": "pass"})
        if auth_response.status_code == 200:
            token = auth_response.json()["access_token"]
            with open("test_dummy.csv", "rb") as f:
                response = client.post(
                    "/api/v1/analyze", 
                    files={"file": f},
                    headers={"Authorization": f"Bearer {token}"}
                )
            if response.status_code == 200:
                print("SUCCESS: Authorized access succeeded (200).")
            else:
                print(f"FAILURE: Authorized access failed with {response.status_code}: {response.text}")
                assert False
        else:
            print("Could not login for valid test.")
            assert False
            
    finally:
        if os.path.exists("test_dummy.csv"):
            os.remove("test_dummy.csv")

if __name__ == "__main__":
    test_analyze_needs_auth()
