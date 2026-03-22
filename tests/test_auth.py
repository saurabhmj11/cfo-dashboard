from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_auth_flow():
    print("Testing Registration...")
    # 1. Register
    response = client.post("/auth/register", json={
        "username": "testuser_auth",
        "email": "test_auth@example.com",
        "password": "password123"
    })
    if response.status_code != 200:
        print(f"Registration failed: {response.text}")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser_auth"
    # assert "hashed_password" not in data # User model in schemas doesn't hide it yet, let's check schema.
    # The response_model is schemas.User, which inherits from UserBase. 
    # UserBase has username, email. User has id, is_active.
    # It does NOT have password. Perfect.
    
    print("Testing Login...")
    # 2. Login
    response = client.post("/auth/token", data={
        "username": "testuser_auth",
        "password": "password123"
    })
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
    assert response.status_code == 200
    token = response.json()
    assert "access_token" in token
    assert token["token_type"] == "bearer"
    print(f"Token received: {token['access_token'][:10]}...")

    print("Testing Duplicate Registration...")
    # 3. Duplicate Register (Should Fail)
    response = client.post("/auth/register", json={
        "username": "testuser_auth",
        "email": "other@example.com",
        "password": "password123"
    })
    assert response.status_code == 400
    print("Duplicate registration correctly rejected.")
    
    print("Testing Bad Password...")
    # 4. Bad Login (Should Fail)
    response = client.post("/auth/token", data={
        "username": "testuser_auth",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
    print("Bad password correctly rejected.")

if __name__ == "__main__":
    test_auth_flow()
    print("Auth flow passed!")
