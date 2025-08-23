import requests
import json

# API endpoint
url = "http://localhost:8000/api/v1/auth/register"

# User data
user_data = {
    "name": "John Doe",
    "email": "johnssmith.doe@example.com",
    "phone": "+918876544210",
    "password": "SecurePass123!",
    "preferred_exam_categories": ["medical", "engineering"],
}

# Make POST request
response = requests.post(url, json=user_data)

# Check response
if response.status_code == 201:
    print("✅ User created successfully!")
    print(json.dumps(response.json(), indent=2))
else:
    print(f"❌ Error: {response.status_code}")
    print(response.json())
