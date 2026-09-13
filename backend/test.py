import requests

r = requests.post(
    "https://anvilgpt.rcac.purdue.edu/api/chat/completions",
    headers={"Authorization": "Bearer sk-07ae883c9a2a40aaa2335958f6c16a39", "Content-Type": "application/json"},
    json={"model": "gpt-oss:120b",
          "messages": [{"role": "user", "content": "Say hello."}],
          "stream": False},
)
print(r.status_code, r.text[:500])