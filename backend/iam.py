"""
Simplified RICE/DICE Integrated Assessment Model

Uses integrated modules to build model and pass required parameters into each other:
- Economy, Emissions, Carbon cycle, Climate, Damage, Abatement
"""

import os
import json
import numpy as np

from modules.economy import EconomyModule
from modules.emissions import EmissionsModule
from modules.carbon_cycle import CarbonCycleModule
from modules.climate import ClimateModule
from modules.damage import DamageModule
from modules.abatement import AbatementModule

# National/Regional Database Parameter Path
_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PARAMS_PATH = os.path.join(_HERE, "data", "params.json")

def load_params(path: str = DEFAULT_PARAMS_PATH) -> dict:
    with open(path) as f:
        return json.load(f)

_params = load_params()
SSP_CONFIGS = _params["ssp_configs"]
REGIONS = _params["regions"]
N_REGIONS = len(REGIONS)

def run_iam(ssp_key: str = "SSP2",  # Default IAM parameters
            start_year: int = 2015,
            end_year: int = 2100,
            params_path: str = DEFAULT_PARAMS_PATH,
            damage_type: str = None,
            ensemble_size: int = None,
            ensemble_seed: int = None,
            cr_start_default: float = None,
            cr_end_default: float = None,
            welfare_type: str = "utilitarian",
            economy_type: str = "market") -> dict:

    params  = load_params(params_path)
    ssp_cfg = params["ssp_configs"][ssp_key]

    if damage_type is not None:
        params["damage"]["damage_type"] = damage_type

    years = np.arange(start_year, end_year + 1)
    n_t = len(years)
    sim_len = float(end_year - start_year)
    n_reg = len(params["regions"])

    # Initialize modules
    econ = EconomyModule(params, ssp_cfg, n_t, economy_type=economy_type)
    emiss = EmissionsModule(params, n_reg, n_t)
    carb = CarbonCycleModule(params, n_t)
    clim = ClimateModule(params, n_t, ensemble_size=ensemble_size, seed=ensemble_seed)
    dmg = DamageModule(params)
    abate = AbatementModule(params)

    # Emissions control rate schedule, linear function from start to end year (applied generally to all regions)
    cr = np.zeros((n_reg, n_t))
    cr_start = cr_start_default if cr_start_default is not None else ssp_cfg["cr_start"]
    cr_end = cr_end_default   if cr_end_default is not None else ssp_cfg["cr_end"]
    cr_year_start = ssp_cfg["cr_start_year"]
    cr_year_end = ssp_cfg["cr_end_year"]
    ramp_len = max(cr_year_start - start_year, 1)

    for ti, yr in enumerate(years):
        if yr < cr_year_start:
            cr_t = cr_start * (yr - start_year) / ramp_len
        elif yr <= cr_year_end:
            cr_t = cr_start + (cr_end - cr_start) * (yr - cr_year_start) / (cr_year_end - cr_year_start)
        else:
            cr_t = cr_end
        cr[:, ti] = np.clip(cr_t, 0.0, 1.0)

    scc_arr = np.zeros(n_t) # Social cost of carbon in $/tCO2, from damage module based on current temp and global GDP
    mac_arr = np.zeros((n_reg, n_t)) # Marginal abatement cost in $/tCO2, based on control rate schedule and carbon intensity from economy module

    # Main Module Loop
    for ti in range(n_t):
        elapsed = float(years[ti] - start_year)

        y_gross, sigma = econ.step_production(ti, elapsed) # Affects carbon intensity and gross output in emissions
        reg_emiss, glob_emiss = emiss.step(ti, elapsed, sim_len, y_gross, sigma, cr[:, ti]) # Affects carbon cycle
        m_at, co2_ppm = carb.step(ti, glob_emiss) # Affects climate
        t_at, forcing = clim.step(ti, m_at, elapsed) # Affects damage
        omega = dmg.compute(t_at) # Affects economy as fraction of gross output lost to climate damage (temp)

        # Welfare-based regional damage distribution
        if welfare_type == "utilitarian" or ti == 0:
            dmg_frac_r = np.full(n_reg, omega)
        else:
            gdppc_prev = np.maximum(econ.gdp_per_capita[:, ti - 1], 1e-6)
            pop_prev = np.maximum(econ.pop[:, ti - 1], 1e-6)
            gdppc_mean = (gdppc_prev * pop_prev).sum() / pop_prev.sum()

            multiplier = np.clip((gdppc_mean / gdppc_prev) ** 0.5, 0.4, 3.0) # Equity multiplier for lower-income countries

            if welfare_type == "egalitarian":
                dmg_frac_r = np.clip(omega * multiplier, 0.0, 0.99)
            else: # Rawlsian, worst-off region
                worst = float(np.clip(omega * multiplier.max(), 0.0, 0.99))
                dmg_frac_r = np.full(n_reg, worst)

        abate_frac = abate.compute(cr[:, ti], sigma, elapsed, start_year) # Affects economy as fraction of gross output spent on abatement
        econ.step_capital(ti, dmg_frac_r, abate_frac) # Affects population, TFP, carbon intensity, and gross output in next period

        scc_arr[ti] = dmg.social_cost_of_carbon(t_at, float(y_gross.sum())) # Effective global damage fraction at current temp times global GDP
        mac_arr[:, ti] = abate.marginal_abatement_cost(cr[:, ti], sigma, elapsed, start_year) # Marginal abatement cost in $/tCO2 for each region at current control rate

    return { # For frontend
        "years": years,
        "emissions": emiss.emissions,
        "global_emissions": emiss.emissions.sum(axis=0),
        "land_emissions": emiss.land_emissions,
        "temperature": clim.t_at_mean,
        "temperature_ensemble": clim.t_at,
        "temperature_p5": clim.percentile(5),
        "temperature_p50": clim.percentile(50),
        "temperature_p95": clim.percentile(95),
        "t_ocean": clim.t_lo.mean(axis=1),
        "forcing": clim.forcing,
        "f_co2": clim.f_co2,
        "f_ex": clim.f_ex,
        "m_at": carb.m_at,
        "co2_ppm": carb.co2_ppm,
        "gdp": econ.y_net,
        "gdp_gross": econ.y_gross,
        "gdp_per_capita": econ.gdp_per_capita,
        "consumption": econ.consumption,
        "population": econ.pop,
        "capital": econ.K,
        "cr": cr,
        "scc": scc_arr,
        "mac": mac_arr,
        "ecs_values": clim.ecs_values,
        "ensemble_size": clim.ensemble_size,
        "ssp": ssp_key,
        "ssp_name": ssp_cfg["name"],
        "ssp_color": ssp_cfg["color"],
    }
