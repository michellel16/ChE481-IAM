"""
Simplified RICE/DICE Integrated Assessment Model — orchestrator.

Loads all parameters from data/params.json (no hard-coded values here)
and coordinates six coupled modules each timestep:

    Step  Module          Key equations
    ----  --------------  --------------------------------------------------
    1     Economy         Cobb-Douglas gross output, TFP & population update
    2     Emissions       E = sigma*(1-mu)*Y + land-use
    3     Carbon cycle    3-box M_AT/M_UP/M_LO update
    4     Climate         Radiative forcing; 2-box T_AT/T_LO update
    5     Damage          Omega = f(T_AT)  [fraction of output lost]
    6     Abatement       Lambda = theta1(t)*mu^theta2  [cost fraction]
    7     Economy         Net output, consumption, capital accumulation

All module implementations live in the modules/ package.
All parameters live in data/params.json.
"""

import os
import json
import numpy as np

from modules.economy      import EconomyModule
from modules.emissions    import EmissionsModule
from modules.carbon_cycle import CarbonCycleModule
from modules.climate      import ClimateModule
from modules.damage       import DamageModule
from modules.abatement    import AbatementModule

# ── default parameter file ────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PARAMS_PATH = os.path.join(_HERE, "data", "params.json")


def load_params(path: str = DEFAULT_PARAMS_PATH) -> dict:
    with open(path) as f:
        return json.load(f)


# ── backwards-compatible module-level exports (used by main.py) ───────────────
_params     = load_params()
SSP_CONFIGS = _params["ssp_configs"]
REGIONS     = _params["regions"]
N_REGIONS   = len(REGIONS)


# ─────────────────────────────────────────────────────────────────────────────
def run_iam(ssp_key: str = "SSP2",
            start_year: int = 2015,
            end_year: int = 2100,
            params_path: str = DEFAULT_PARAMS_PATH,
            damage_type: str = None,
            ensemble_size: int = None,
            ensemble_seed: int = None) -> dict:
    """
    Run the simplified RICE/DICE IAM for one SSP scenario.

    Parameters
    ----------
    ssp_key       : one of "SSP1" ... "SSP5"
    start_year    : simulation start year
    end_year      : simulation end year
    params_path   : path to params.json (defaults to data/params.json)
    damage_type   : override damage function ('quadratic', 'linear', 'threshold')
                    If None, uses the value in params.json
    ensemble_size : number of climate ensemble members.
                    None  → use params["ensemble"]["size"] (default 20).
                    1     → single deterministic run.
                    N > 1 → N members with ECS sampled from log-normal.
    ensemble_seed : random seed override for ECS sampling (None → use params).

    Returns
    -------
    dict containing time-series arrays for emissions, temperature, GDP,
    population, CO2 concentration, forcing, MAC, SCC, and scenario metadata.
    Keys:
        years, emissions (n_regions x n_t), global_emissions, land_emissions,
        temperature        — ensemble mean T_AT (n_t,)
        temperature_ensemble — full ensemble T_AT (n_t, ensemble_size)
        temperature_p5 / temperature_p50 / temperature_p95 — percentiles (n_t,)
        t_ocean (ensemble mean T_LO, n_t), forcing, f_co2, f_ex,
        m_at, co2_ppm, gdp (net), gdp_gross, gdp_per_capita, consumption,
        population, capital, mu, scc, mac (n_regions x n_t),
        ecs_values (ensemble_size,), ensemble_size,
        ssp, ssp_name, ssp_color
    """
    params  = load_params(params_path)
    ssp_cfg = params["ssp_configs"][ssp_key]

    if damage_type is not None:
        params["damage"]["damage_type"] = damage_type

    years   = np.arange(start_year, end_year + 1)
    n_t     = len(years)
    sim_len = float(end_year - start_year)
    n_reg   = len(params["regions"])

    # ── initialise modules ────────────────────────────────────────────────────
    econ  = EconomyModule(params, ssp_cfg, n_t)
    emiss = EmissionsModule(params, n_reg, n_t)
    carb  = CarbonCycleModule(params, n_t)
    clim  = ClimateModule(params, n_t,
                          ensemble_size=ensemble_size,
                          seed=ensemble_seed)
    dmg   = DamageModule(params)
    abate = AbatementModule(params)

    # ── emission control rate schedule ────────────────────────────────────────
    # Linear ramp from mu_start (at mu_start_year) to mu_end (at mu_end_year);
    # applied uniformly across regions (can be made region-specific if needed).
    mu = np.zeros((n_reg, n_t))
    mu_s, yr_s = ssp_cfg["mu_start"],    ssp_cfg["mu_start_year"]
    mu_e, yr_e = ssp_cfg["mu_end"],      ssp_cfg["mu_end_year"]
    ramp_len   = max(yr_s - start_year, 1)
    for ti, yr in enumerate(years):
        if yr < yr_s:
            mu_t = mu_s * (yr - start_year) / ramp_len
        elif yr <= yr_e:
            mu_t = mu_s + (mu_e - mu_s) * (yr - yr_s) / (yr_e - yr_s)
        else:
            mu_t = mu_e
        mu[:, ti] = np.clip(mu_t, 0.0, 1.0)

    # ── diagnostic arrays ─────────────────────────────────────────────────────
    scc_arr = np.zeros(n_t)
    mac_arr = np.zeros((n_reg, n_t))

    # ── main time loop ────────────────────────────────────────────────────────
    for ti in range(n_t):
        elapsed = float(years[ti] - start_year)

        # 1. Economy — production (needs to come before emissions)
        y_gross, sigma = econ.step_production(ti, elapsed)

        # 2. Emissions — energy/industrial + land-use
        reg_emiss, glob_emiss = emiss.step(
            ti, elapsed, sim_len, y_gross, sigma, mu[:, ti])

        # 3. Carbon cycle — update reservoir stocks
        m_at, co2_ppm = carb.step(ti, glob_emiss)

        # 4. Climate — forcing and temperature
        t_at, forcing = clim.step(ti, m_at, elapsed)

        # 5. Damage — output loss fraction from temperature
        dmg_frac = dmg.compute(t_at)

        # 6. Abatement — cost fraction of gross output
        abate_frac = abate.compute(mu[:, ti], elapsed)

        # 7. Economy — net output, consumption, capital for next period
        econ.step_capital(ti, dmg_frac, abate_frac)

        # 8. Diagnostics
        scc_arr[ti]    = dmg.social_cost_of_carbon(t_at, float(y_gross.sum()))
        mac_arr[:, ti] = abate.marginal_abatement_cost(mu[:, ti], sigma, elapsed)

    return {
        "years":                 years,
        "emissions":             emiss.emissions,
        "global_emissions":      emiss.emissions.sum(axis=0),
        "land_emissions":        emiss.land_emissions,
        # temperature: ensemble mean (n_t,) — backwards-compatible scalar series
        "temperature":           clim.t_at_mean,
        # full ensemble and percentile bands (n_t,)
        "temperature_ensemble":  clim.t_at,
        "temperature_p5":        clim.percentile(5),
        "temperature_p50":       clim.percentile(50),
        "temperature_p95":       clim.percentile(95),
        "t_ocean":               clim.t_lo.mean(axis=1),
        "forcing":               clim.forcing,
        "f_co2":                 clim.f_co2,
        "f_ex":                  clim.f_ex,
        "m_at":                  carb.m_at,
        "co2_ppm":               carb.co2_ppm,
        "gdp":                   econ.y_net,
        "gdp_gross":             econ.y_gross,
        "gdp_per_capita":        econ.gdp_per_capita,
        "consumption":           econ.consumption,
        "population":            econ.pop,
        "capital":               econ.K,
        "mu":                    mu,
        "scc":                   scc_arr,
        "mac":                   mac_arr,
        "ecs_values":            clim.ecs_values,
        "ensemble_size":         clim.ensemble_size,
        "ssp":                   ssp_key,
        "ssp_name":              ssp_cfg["name"],
        "ssp_color":             ssp_cfg["color"],
    }
