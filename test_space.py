import os, sys, json, requests

SPACE = os.environ.get("SPACE_URL", "https://shivareeves-voice-backend.hf.space")
HF_TOKEN = os.environ.get("HF_TOKEN", "")

headers = {}
if HF_TOKEN.strip():
    headers["Authorization"] = f"Bearer {HF_TOKEN}"

def get(url):
    r = requests.get(url, headers=headers, timeout=20)
    return r.status_code, r.headers.get("content-type",""), r.text

def post(url, data):
    r = requests.post(url, headers={"Content-Type":"application/json", **headers}, json=data, timeout=60)
    return r.status_code, r.headers.get("content-type",""), r.text

print("SPACE =", SPACE)

# 1) /config
code, ctype, text = get(f"{SPACE.rstrip('/')}/config")
print("\nGET /config ->", code, ctype)
if code == 200:
    try:
        cfg = json.loads(text)
        print("api_prefix:", cfg.get("api_prefix"))
    except Exception:
        print("Non-JSON:", text[:200])
else:
    print("Body:", text[:200])

# 2) Try routes + payloads
combos = [
    ("/run/predict",  {"data": ["You are concise.","Say hi in one sentence."]}),
    ("/run/predict",  {"data": ["Say hi in one sentence."]}),
    ("/api/predict/", {"data": ["You are concise.","Say hi in one sentence."]}),
    ("/api/predict/", {"data": ["Say hi in one sentence."]}),
]

for route, data in combos:
    url = f"{SPACE.rstrip('/')}{route}"
    print(f"\nPOST {url}  body={data}")
    try:
        code, ctype, text = post(url, data)
        print("->", code, ctype)
        if code in (200, 422):
            try:
                j = json.loads(text)
                print("JSON:", json.dumps(j, indent=2)[:500])
                if isinstance(j, dict) and "data" in j and isinstance(j["data"], list):
                    print("\n✅ Reply:", j["data"][0])
                    break
            except Exception:
                print("Body:", text[:300])
        else:
            print("Body:", text[:300])
    except requests.RequestException as e:
        print("Request error:", e)
