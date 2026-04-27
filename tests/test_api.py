import requests
import json
import random

url = "http://127.0.0.1:8000/api/ai-onboarding"

# Generate a random email so the database unique constraint doesn't fail on multiple runs
random_email = f"jane.smith.{random.randint(1000, 9999)}@example.com"

print("--- Test 1: Incomplete Information ---")
payload1 = {
    "text": f"Hi, please onboard Jane Smith. Her email is {random_email}."
}
try:
    res1 = requests.post(url, json=payload1)
    print("Status:", res1.status_code)
    data1 = res1.json()
    print(json.dumps(data1, indent=2))
    
    thread_id = data1.get("thread_id")
    
    if thread_id and data1.get("status") == "missing_info":
        print("\n--- Test 2: Providing Remaining Information ---")
        payload2 = {
            "text": "Sorry, here is the rest: She is Female, born 1990-05-15. Mobile is 9876543210. Single, blood group O+. Her middle name is Marie.",
            "thread_id": thread_id
        }
        res2 = requests.post(url, json=payload2)
        print("Status:", res2.status_code)
        print(json.dumps(res2.json(), indent=2))
        
except Exception as e:
    print(f"Connection failed: {e}")
