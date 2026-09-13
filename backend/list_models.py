import os, requests

r = requests.get(
    "https://anvilgpt.rcac.purdue.edu/api/models",
    headers={"Authorization": f"Bearer {os.environ['ANVILGPT_API_KEY']}"},
)
print(r.status_code)
for m in r.json().get("data", []):
    print(m.get("id"))
