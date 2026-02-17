import requests

# Direct test of Groq API
api_key = "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"

url = "https://api.groq.com/openai/v1/chat/completions"

payload = {
    "model": "llama-3.3-70b-versatile",
    "messages": [
        {"role": "user", "content": "Say hello"}
    ]
}

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}",
    "User-Agent": "Mozilla/5.0"
}

print("Testing Groq API directly with requests...")
try:
    response = requests.post(url, json=payload, headers=headers, timeout=30, verify=True)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("SUCCESS!")
        print(response.json())
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}")
