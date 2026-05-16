import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend"))

from backend.modules.climate.fair_climate import _find_fair_data_path, download_fair_data
if _find_fair_data_path() is None:
    print("FAIR data files not found at startup; downloading now…", flush=True)
    download_fair_data()

from app import server  # noqa: E402 — used by gunicorn as wsgi:server
