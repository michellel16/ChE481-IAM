"""
IAM Backend API — Flask REST server.
Run:  python backend/api.py   (default port 5001)

Endpoints
---------
GET  /api/config          → SSP names/defaults and region list
POST /api/run             → run the IAM model, return results as JSON
"""

import gc
import os
import sys
import json
import numpy as np
from flask import Flask, request, jsonify

# Make backend/ importable regardless of working directory
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from iam_model import run_iam, SSP_CONFIGS, REGIONS  # noqa: E402

app = Flask(__name__)


def _to_list(arr):
    if isinstance(arr, np.ndarray):
        return arr.tolist()
    return arr


@app.route("/api/config", methods=["GET"])
def get_config():
    """Return static UI configuration (SSP options + region names)."""
    return jsonify({
        "ssp_configs": {
            k: {
                "name":           v["name"],
                "color":          v["color"],
                "mu_start":       v["mu_start"],
                "mu_end":         v["mu_end"],
                "mu_start_year":  v["mu_start_year"],
                "mu_end_year":    v["mu_end_year"],
            }
            for k, v in SSP_CONFIGS.items()
        },
        "regions": REGIONS,
    })


@app.route("/api/run", methods=["POST"])
def run():
    """
    Run the IAM model.

    Expected JSON body
    ------------------
    {
        "ssp":       "SSP2",
        "start":     2015,
        "end":       2100,
        "damage":    "quadratic",
        "ensemble":  10,
        "mu_start":  0.10,
        "mu_end":    0.65
    }

    Returns
    -------
    JSON with all time-series results as plain lists.
    """
    body = request.get_json(force=True)

    ssp      = body.get("ssp",      "SSP2")
    start    = int(body.get("start", 2015))
    end      = int(body.get("end",   2100))
    damage   = body.get("damage",   "quadratic")
    ensemble = max(1, min(int(body.get("ensemble", 10)), 30))
    mu_start = float(body.get("mu_start", 0.10))
    mu_end   = float(body.get("mu_end",   0.65))
    welfare  = body.get("welfare",  "utilitarian")
    economy  = body.get("economy",  "market")

    if start >= end:
        return jsonify({"error": "start year must be before end year"}), 400

    r = run_iam(
        ssp_key=ssp,
        start_year=start,
        end_year=end,
        damage_type=damage,
        ensemble_size=ensemble,
        mu_start_override=mu_start,
        mu_end_override=mu_end,
        welfare_type=welfare,
        economy_type=economy,
    )

    payload = {
        "years":               _to_list(r["years"]),
        "global_emissions":    _to_list(r["global_emissions"]),
        "land_emissions":      _to_list(r["land_emissions"]),
        "emissions":           _to_list(r["emissions"]),
        "mu":                  _to_list(r["mu"]),
        "temperature":         _to_list(r["temperature"]),
        "temperature_p5":      _to_list(r["temperature_p5"]),
        "temperature_p50":     _to_list(r["temperature_p50"]),
        "temperature_p95":     _to_list(r["temperature_p95"]),
        "temperature_ensemble": _to_list(r["temperature_ensemble"]) if ensemble <= 20 else None,
        "ecs_values":          _to_list(r["ecs_values"]),
        "ensemble_size":       ensemble,
        "t_ocean":             _to_list(r["t_ocean"]),
        "forcing":             _to_list(r["forcing"]),
        "f_co2":               _to_list(r["f_co2"]),
        "f_ex":                _to_list(r["f_ex"]),
        "co2_ppm":             _to_list(r["co2_ppm"]),
        "gdp":                 _to_list(r["gdp"]),
        "gdp_gross":           _to_list(r["gdp_gross"]),
        "gdp_per_capita":      _to_list(r["gdp_per_capita"]),
        "scc":                 _to_list(r["scc"]),
        "mac":                 _to_list(r["mac"]),
        "ssp":                 r["ssp"],
        "ssp_name":            r["ssp_name"],
    }
    del r
    gc.collect()
    return jsonify(payload)


if __name__ == "__main__":
    port = int(os.environ.get("IAM_BACKEND_PORT", 5001))
    print(f"IAM backend listening on http://localhost:{port}")
    app.run(port=port, debug=False)
