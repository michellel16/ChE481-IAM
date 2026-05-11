import os
import sys

_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, _BACKEND)

from iam import run_iam, SSP_CONFIGS, REGIONS  # noqa: E402

SSP_OPTIONS        = [{"label": v["name"], "value": k} for k, v in SSP_CONFIGS.items()]
REGION_OPTIONS     = [{"label": r, "value": i} for i, r in enumerate(REGIONS)]
ALL_REGION_INDICES = list(range(len(REGIONS)))
