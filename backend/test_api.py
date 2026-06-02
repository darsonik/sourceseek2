import requests

try:
    print("Testing login...")
    res = requests.post("http://127.0.0.1:8000/api/v1/auth/register", json={"username": "testuser_debug", "password": "password"})
    if res.status_code == 400:
        res = requests.post("http://127.0.0.1:8000/api/v1/auth/login", json={"username": "testuser_debug", "password": "password"})
    print("Login response:", res.status_code, res.text)
    
    token = res.json().get("access_token")
    if token:
        print("Got token, testing documents endpoint...")
        res2 = requests.get("http://127.0.0.1:8000/api/v1/documents", headers={"Authorization": f"Bearer {token}"})
        print("Documents response:", res2.status_code, res2.text)
except Exception as e:
    print(e)
