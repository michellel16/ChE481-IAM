"""
IAM Backend API — Flask REST server
Run:  python backend/api.py   (default port 5001)

Endpoints
---------
GET  /api/config -> send SSP and region list
POST /api/run -> run  IAM model, return results as JSON
"""

import gc
import os
import sys
import numpy as np
from flask import Flask, request, jsonify

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from iam import run_iam, SSP_CONFIGS, REGIONS  # noqa: E402
app = Flask(__name__)

def _to_list(arr):
    if isinstance(arr, np.ndarray):
        return arr.tolist()
    return arr

@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify({ # Return SSP and region configs from frontend input
        "ssp_configs": {
            k: {
                "name":           v["name"],
                "color":          v["color"],
                "cr_start":       v["cr_start"],
                "cr_end":         v["cr_end"],
                "cr_start_year":  v["cr_start_year"],
                "cr_end_year":    v["cr_end_year"],
            }
            for k, v in SSP_CONFIGS.items()
        },
        "regions": REGIONS,
    })

@app.route("/api/run", methods=["POST"])
def run():
    body = request.get_json(force=True)

    ssp = body.get("ssp",      "SSP2")
    start = int(body.get("start", 2025))
    end = int(body.get("end",   2100))
    damage = body.get("damage",   "quadratic")
    ensemble = max(1, min(int(body.get("ensemble", 10)), 30))
    cr_start = float(body.get("cr_start", 0.10))
    cr_end = float(body.get("cr_end",   0.65))
    welfare = body.get("welfare",  "utilitarian")
    economy = body.get("economy",  "market")
    climate = body.get("climate",  "dice")

    if start >= end:
        return jsonify({"error": "start year must be before end year"}), 400

    r = run_iam(
        ssp_key = ssp,
        start_year = start,
        end_year = end,
        damage_type = damage,
        ensemble_size = ensemble,
        cr_start_default = cr_start,
        cr_end_default = cr_end,
        welfare_type = welfare,
        economy_type = economy,
        climate_type = climate,
    )

    payload = {
        "years": _to_list(r["years"]),
        "global_emissions": _to_list(r["global_emissions"]),
        "land_emissions": _to_list(r["land_emissions"]),
        "emissions": _to_list(r["emissions"]),
        "cr": _to_list(r["cr"]),
        "temperature": _to_list(r["temperature"]),
        "temperature_p5": _to_list(r["temperature_p5"]),
        "temperature_p50": _to_list(r["temperature_p50"]),
        "temperature_p95": _to_list(r["temperature_p95"]),
        "temperature_ensemble": _to_list(r["temperature_ensemble"]) if ensemble <= 20 else None,
        "ecs_values": _to_list(r["ecs_values"]),
        "ensemble_size": ensemble,
        "t_ocean": _to_list(r["t_ocean"]),
        "forcing": _to_list(r["forcing"]),
        "f_co2": _to_list(r["f_co2"]),
        "f_ex": _to_list(r["f_ex"]),
        "co2_ppm": _to_list(r["co2_ppm"]),
        "gdp": _to_list(r["gdp"]),
        "gdp_gross": _to_list(r["gdp_gross"]),
        "gdp_per_capita": _to_list(r["gdp_per_capita"]),
        "scc": _to_list(r["scc"]),
        "mac": _to_list(r["mac"]),
        "ssp": r["ssp"],
        "ssp_name": r["ssp_name"],
        "welfare_type": r.get("welfare_type", welfare),
        "damage_type":  r.get("damage_type",  damage),
        "climate_type": r.get("climate_type", climate),
        "welfare":               float(r["welfare"]),
        "welfare_per_year":      _to_list(r["welfare_per_year"]),
        "equity_equiv_consumption": _to_list(r["equity_equiv_consumption"]),
        "regional_welfare":      _to_list(r["regional_welfare"]),
        "gini_per_year":         _to_list(r["gini_per_year"]),
        "regional_damage_frac":  _to_list(r["regional_damage_frac"]),
        "consumption":           _to_list(r["consumption"]),
        "population":            _to_list(r["population"]),
    }

    del r
    gc.collect()
    return jsonify(payload)

if __name__ == "__main__":
    port = int(os.environ.get("IAM_BACKEND_PORT", 5001))
    print(f"IAM backend listening on http://localhost:{port}")
    app.run(port=port, debug=False)
