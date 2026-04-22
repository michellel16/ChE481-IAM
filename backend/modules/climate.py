"""
Climate module considers radiative forcing and climate-damage relationship, 2-box model (surface and deep ocean)
Uses climate model ensemble to determine Equilibrium Climate Sensitivity (ECS) (plausible temperature outcomes) from a probability distribution.

Determines ECS distribution, radiative forcing (same for all ensemble), temperature dynamics, returns mean for damage and economy module
Simplified representation:
- Climate eqn calculates mean surface temperature of globe and deep ocean
- Forcing eqn calculates impact of emissions on radiation balance of globe
"""

import numpy as np


class ClimateModule:
    # Energy-balance climate model and a radiative forcing that depends on atmospheric carbon stock.

    def __init__(self, params: dict, n_years: int, ensemble_size: int = None, seed: int = None):
        cp = params["climate"]
        ep = params.get("ensemble", {})

        if ensemble_size is None: ensemble_size = ep.get("size", 1)
        self.ensemble_size = max(1, int(ensemble_size))

        # Climate model parameters for all ensemble
        self.eta = cp["eta"]
        self.c1 = cp["c1"]
        self.c3 = cp["c3"]
        self.c4 = cp["c4"]
        self.f_ex_2015 = cp["f_ex_2015"]
        self.f_ex_2100 = cp["f_ex_2100"]
        self.m_at_pre = params["carbon_cycle"]["m_at_preindustrial"]

        self.ecs_values = self._sample_ecs(cp, ep, seed) # ECS values, one per ensemble member
        self.lam_values = self.eta / self.ecs_values

        self.t_at = np.zeros((n_years, self.ensemble_size))
        self.t_lo = np.zeros((n_years, self.ensemble_size))

        self.forcing = np.zeros(n_years) # Radiative forcing
        self.f_co2 = np.zeros(n_years)
        self.f_ex = np.zeros(n_years)

        self.t_at[0, :] = cp["t_at_2015"] # Initial conditions, start year at 2015
        self.t_lo[0, :] = cp["t_lo_2015"]

    def _sample_ecs(self, cp: dict, ep: dict, seed) -> np.ndarray:
        if self.ensemble_size == 1: return np.array([cp["ecs"]])

        _seed = seed if seed is not None else ep.get("seed", 42)
        ecs_median = ep.get("ecs_median", 3.0)
        sigma_log = ep.get("ecs_sigma_log", 0.25)
        ecs_min = ep.get("ecs_min", 1.5)
        ecs_max = ep.get("ecs_max", 6.0)

        rng = np.random.default_rng(_seed) # Randomize ensemble seed
        raw = rng.lognormal(np.log(ecs_median), sigma_log, self.ensemble_size)
        return np.clip(raw, ecs_min, ecs_max)

    # Determine radiative forcing and temperatures for current time step for whole ensemble
    def step(self, t: int, m_at: float, elapsed: float):
        self.f_co2[t] = self.eta * np.log2(max(m_at / self.m_at_pre, 1e-9)) # Forcing, only dependent on atmospheric CO2

        frac = min(elapsed / 85.0, 1.0) # Forcing not from CO2 ramping up
        self.f_ex[t] = self.f_ex_2015 + (self.f_ex_2100 - self.f_ex_2015) * frac
        self.forcing[t] = self.f_co2[t] + self.f_ex[t]

        if t < self.t_at.shape[0] - 1: # Advance temperature dynamics for one year, for all ensemble members
            self.t_at[t + 1, :] = (self.t_at[t, :] + self.c1 * (self.forcing[t] - self.lam_values * self.t_at[t, :] - self.c3 * (self.t_at[t, :] - self.t_lo[t, :])))
            self.t_lo[t + 1, :] = (self.t_lo[t, :]
                                   + self.c4 * (self.t_at[t, :] - self.t_lo[t, :]))

        return float(self.t_at[t, :].mean()), self.forcing[t]

    @property
    def t_at_mean(self) -> np.ndarray:
        """Ensemble mean surface temperature (N years)"""
        return self.t_at.mean(axis=1)

    @property
    def t_at_median(self) -> np.ndarray:
        """Ensemble median surface temperature (n_years,)."""
        return np.median(self.t_at, axis=1)

    # Percentile of ensemble temperature at each timestep
    def percentile(self, p: float) -> np.ndarray:
        return np.percentile(self.t_at, p, axis=1)

    # Equilibrium temperature for sustained forcing, for ensemble member
    def equilibrium_temperature(self, forcing: float, member: int = 0) -> float:
        return forcing / self.lam_values[member]

    def years_above_threshold(self, threshold_c: float, use_mean: bool = True) -> int:
        if use_mean: return int(np.sum(self.t_at_mean > threshold_c))
        counts = np.sum(self.t_at > threshold_c, axis=0)
        return int(np.median(counts))
