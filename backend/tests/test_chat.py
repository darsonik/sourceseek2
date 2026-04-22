import requests

print("First request...")
res = requests.post("http://127.0.0.1:8002/api/v1/search/", json={"query": "test query", "thread_id": "test_thread_2"})
print("Status:", res.status_code)
print("Response:", res.json())

print("Second request...")
res2 = requests.post("http://127.0.0.1:8002/api/v1/search/", json={"query": "follow up", "thread_id": "test_thread_2"})
print("Status:", res2.status_code)
print("Response:", res2.json())
