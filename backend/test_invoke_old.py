import os
import requests

response = requests.post("http://localhost:8000/api/chat", json={"message": "Bonjour"})
print(response.json())
