import requests
import time

URL = "http://127.0.0.1:8000/auth/token"
# Use register first to ensure user exists
REGISTER_URL = "http://127.0.0.1:8000/auth/register"

def test_auth_flow():
    print("1. Testing Backend Connectivity...")
    try:
        requests.get("http://127.0.0.1:8000/")
        print("   [OK] Backend is reachable.")
    except Exception as e:
        print(f"   [FAIL] Backend unreachable: {e}")
        return

    username = f"debug_user_{int(time.time())}"
    password = "password123"
    
    print(f"\n2. Registering User: {username}")
    try:
        res = requests.post(REGISTER_URL, json={"username": username, "email": f"{username}@example.com", "password": password})
        print(f"   Status: {res.status_code}")
        print(f"   Response: {res.text}")
    except Exception as e:
        print(f"   [FAIL] Register Exception: {e}")

    print(f"\n3. Logging In (Getting Token)...")
    start = time.time()
    try:
        # OAuth form data
        res = requests.post(URL, data={"username": username, "password": password})
        duration = time.time() - start
        
        print(f"   Status: {res.status_code}")
        print(f"   Duration: {duration:.2f} seconds")
        if duration > 2.0:
            print("   [WARNING] Login took > 2 seconds!")
        
        if res.status_code == 200:
            print("   [SUCCESS] Token received.")
        else:
            print(f"   [FAIL] Login failed: {res.text}")
            
    except Exception as e:
        print(f"   [FAIL] Login Exception: {e}")

if __name__ == "__main__":
    test_auth_flow()
