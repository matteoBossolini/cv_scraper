import requests
import json

# API endpoint
url = "https://app.wordware.ai/api/released-app/1abe3cff-6ec3-43c6-9e19-9af6e1f4a21f/run"

# Request body
payload = {
    "inputs": {
        "cv": {
            "type": "file",
            "file_type": "your_file_type",
            "file_url": "your_file_url",
            "file_name": "your_file_name"
        },
        "report": {
            "type": "file", 
            "file_type": "your_file_type",
            "file_url": "your_file_url",
            "file_name": "your_file_name"
        }
    },
    "version": "1.0"
}

# Make POST request
response = requests.post(url, json=payload)

# Print response
print(response.status_code)
print(response.json())