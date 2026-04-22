import os
import json
import urllib.request
import urllib.error

BACKEND_URL = os.environ.get("IAM_BACKEND_URL", "http://localhost:5001")

def _api_get(path: str) -> dict:
    with urllib.request.urlopen(f"{BACKEND_URL}{path}", timeout=10) as resp:
        return json.loads(resp.read())

def _api_post(path: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req  = urllib.request.Request(
        f"{BACKEND_URL}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())

try:
    _config     = _api_get("/api/config")
    SSP_CONFIGS = _config["ssp_configs"]
    REGIONS     = _config["regions"]
except Exception as exc:
    raise RuntimeError(
        f"Cannot reach IAM backend at {BACKEND_URL}. "
        "Start it first:  python backend/api.py"
    ) from exc

SSP_OPTIONS        = [{"label": v["name"], "value": k} for k, v in SSP_CONFIGS.items()]
REGION_OPTIONS     = [{"label": r, "value": i} for i, r in enumerate(REGIONS)]
ALL_REGION_INDICES = list(range(len(REGIONS)))
