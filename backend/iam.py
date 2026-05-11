"""
Simplified RICE/DICE Integrated Assessment Model

Uses integrated modules to build model and pass required parameters into each other:
- Economy, Emissions, Carbon cycle, Climate, Damage, Abatement, Welfare
"""

import os
import json
import numpy as np

from modules.economy import EconomyModule
from modules.emissions import EmissionsModule
from modules.carbon_cycle import CarbonCycleModule
from modules.climate.climate import ClimateModule
from modules.damage import DamageModule
from modules.abatement import AbatementModule
from modules.welfare import WelfareModule

# National/Regional Database Parameter Path
_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PARAMS_PATH = os.path.join(_HERE, "data", "params.json")


def load_params(path: str = DEFAULT_PARAMS_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)

_params = load_params()
SSP_CONFIGS = _params["ssp_configs"]
REGIONS = _params["regions"]
N_REGIONS = len(REGIONS)


def run_iam(
    ssp_key: str = "SSP2",
    start_year: int = 2025,
    end_year: int = 2100,
    params_path: str = DEFAULT_PARAMS_PATH,
    damage_type: str = None,
    ensemble_size: int = None,
    ensemble_seed: int = None,
    cr_start_default: float = None,
    cr_end_default: float = None,
    welfare_type: str = None,
    economy_type: str = "market",
    climate_type: str = None,
) -> dict:

    params = load_params(params_path)
    ssp_cfg = params["ssp_configs"][ssp_key]

    if damage_type is not None:
        params["damage"]["type"] = damage_type
        params["damage"]["damage_type"] = damage_type  # backward compat

    resolved_welfare = (
        welfare_type
        or params.get("welfare", {}).get("type", "utilitarian")
    )
    resolved_climate = (
        climate_type
        or params.get("climate", {}).get("type", "dice")
    ).lower()

    years = np.arange(start_year, end_year + 1)
    n_t = len(years)
    sim_len = float(end_year - start_year)
    n_reg = len(params["regions"])

    econ = EconomyModule(params, ssp_cfg, n_t, economy_type=economy_type)
    emiss = EmissionsModule(params, n_reg, n_t)
    dmg = DamageModule(params)
    abate = AbatementModule(params)
    welfare_mod = WelfareModule(resolved_welfare, params)

    use_fair = (resolved_climate == "fair")
    carb = None
    clim = None
    fair_clim = None

    if use_fair:
        from modules.climate.fair_climate import FAIRClimateModule
        fair_clim = FAIRClimateModule(
            params,
            n_t,
            start_year=start_year,
            ensemble_size=ensemble_size or 1,
            seed=ensemble_seed or 42,
        )
        carb = CarbonCycleModule(params, n_t)
    else:
        carb = CarbonCycleModule(params, n_t)
        clim = ClimateModule(
            params, n_t,
            ensemble_size=ensemble_size,
            seed=ensemble_seed,
            start_year=start_year,
        )

    # Emission control rate schedule
    cr = np.zeros((n_reg, n_t))
    cr_start = cr_start_default if cr_start_default is not None else ssp_cfg["cr_start"]
    cr_end = cr_end_default if cr_end_default is not None else ssp_cfg["cr_end"]
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

    scc_arr = np.zeros(n_t)
    mac_arr = np.zeros((n_reg, n_t))
    dmg_frac_arr = np.zeros((n_reg, n_t))

    # Main simulation loop
    for ti in range(n_t):
        elapsed = float(years[ti] - start_year)

        y_gross, sigma = econ.step_production(ti, elapsed)
        reg_emiss, glob_emiss = emiss.step(ti, elapsed, sim_len, y_gross, sigma, cr[:, ti])

        if use_fair:
            t_at, forcing = fair_clim.step(ti, glob_emiss, elapsed)
            m_at, co2_ppm = carb.step(ti, glob_emiss)
        else:
            m_at, co2_ppm = carb.step(ti, glob_emiss)
            t_at, forcing = clim.step(ti, m_at, elapsed)

        omega = dmg.calculate_damage_frac(t_at)

        # Welfare-based regional damage distribution
        # Utilitarian: uniform damage. All other frameworks: redistribute by GDP per capita.
        if resolved_welfare == "utilitarian" or ti == 0:
            dmg_frac_r = np.full(n_reg, omega)
        else:
            gdppc_prev = np.maximum(econ.gdp_per_capita[:, ti - 1], 1e-6)
            pop_prev   = np.maximum(econ.pop[:, ti - 1], 1e-6)
            gdppc_mean = (gdppc_prev * pop_prev).sum() / pop_prev.sum()
            if resolved_welfare == "prioritarian":
                exponent = 1.0
            elif resolved_welfare == "egalitarian":
                exponent = 0.3
            else:
                exponent = 0.5
            multiplier = np.clip((gdppc_mean / gdppc_prev) ** exponent, 0.4, 3.0)
            dmg_frac_r = np.clip(omega * multiplier, 0.0, 0.99)

        dmg_frac_arr[:, ti] = dmg_frac_r
        abate_frac = abate.compute(cr[:, ti], sigma, elapsed, start_year)
        econ.step_capital(ti, dmg_frac_r, abate_frac)

        scc_arr[ti] = dmg.social_cost_of_carbon(t_at, float(y_gross.sum()))
        mac_arr[:, ti] = abate.marginal_abatement_cost(cr[:, ti], sigma, elapsed, start_year)

    # Welfare aggregation
    welfare_results = welfare_mod.compute(
        econ.consumption / np.maximum(econ.pop, 1e-9),  # consumption per capita
        econ.pop,
        years,
    )
    regional_welfare = welfare_mod.regional_welfare(
        econ.consumption / np.maximum(econ.pop, 1e-9),
        years,
    )

    # Collect climate module outputs
    active_clim = fair_clim if use_fair else clim

    return {
        "years": years,
        "emissions": emiss.emissions,
        "global_emissions": emiss.emissions.sum(axis=0),
        "land_emissions": emiss.land_emissions,
        "temperature": active_clim.t_at_mean,
        "temperature_ensemble": active_clim.t_at,
        "temperature_p5": active_clim.percentile(5),
        "temperature_p50": active_clim.percentile(50),
        "temperature_p95": active_clim.percentile(95),
        "t_ocean": active_clim.t_lo.mean(axis=1),
        "forcing": active_clim.forcing,
        "f_co2": active_clim.f_co2,
        "f_ex": active_clim.f_ex,
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
        "ecs_values": active_clim.ecs_values,
        "ensemble_size": active_clim.ensemble_size,
        "ssp": ssp_key,
        "ssp_name": ssp_cfg["name"],
        "ssp_color": ssp_cfg["color"],
        "welfare": welfare_results["welfare"],
        "welfare_per_year": welfare_results["welfare_per_year"],
        "equity_equiv_consumption": welfare_results["equity_equiv_consumption"],
        "regional_welfare": regional_welfare,
        "gini_per_year": welfare_results["gini_per_year"],
        "regional_damage_frac": dmg_frac_arr,
        "welfare_type": resolved_welfare,
        "climate_type": resolved_climate,
        "damage_type": params["damage"].get("type", "quadratic"),
    }
