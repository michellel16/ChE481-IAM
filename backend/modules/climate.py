"""
Climate module — radiative forcing and 2-box temperature model with ensemble support.

A climate model ensemble runs multiple simulations, each with a different value
of Equilibrium Climate Sensitivity (ECS) drawn from a probability distribution.
Because no single value of ECS is known precisely, running an ensemble quantifies
the range of plausible temperature outcomes and gives a statistically robust
estimate (mean ± uncertainty band) rather than a single deterministic projection.

ECS distribution (IPCC AR6):
  - Log-normal is used because ECS must be positive and the distribution is
    right-skewed.  Parameterised as: median = ecs_median, spread = ecs_sigma_log.
  - IPCC AR6 best estimate: 3.0 degC; likely range: 2.5–4.0 degC.

Radiative forcing (same for all ensemble members — forcing depends only on M_AT):
    F_CO2(t) = eta * log2(M_AT(t) / M_AT_preindustrial)   [W/m^2]
    F_EX(t)  = exogenous non-CO2 ramp                     [W/m^2]
    F(t)     = F_CO2(t) + F_EX(t)

Temperature dynamics (2-box, vectorised over ensemble members e):
    T_AT(t+1,e) = T_AT(t,e) + c1*[F(t) - lambda(e)*T_AT(t,e) - c3*(T_AT(t,e)-T_LO(t,e))]
    T_LO(t+1,e) = T_LO(t,e) + c4*(T_AT(t,e) - T_LO(t,e))

    lambda(e) = eta / ECS(e)   — varies per ensemble member

The step() method returns the ensemble mean T_AT for use in the damage/economy
modules.  The full ensemble (t_at) is available as an attribute for analysis.
"""

import numpy as np


class ClimateModule:
    """
    2-box energy-balance climate model with optional multi-member ensemble.

    Parameters
    ----------
    params        : full parameter dict from params.json
    n_years       : number of simulation timesteps
    ensemble_size : number of ensemble members.
                    - 1 (default if omitted)  → single deterministic run using
                      the ECS value in params["climate"]["ecs"].
                    - N > 1                   → sample N ECS values from the
                      log-normal distribution specified in params["ensemble"].
                    - None                    → use params["ensemble"]["size"].
    seed          : random seed override (None → use params["ensemble"]["seed"]).

    Key attributes
    --------------
    t_at          : (n_years, ensemble_size) surface temperature anomaly [degC]
    t_lo          : (n_years, ensemble_size) deep-ocean temperature anomaly [degC]
    forcing       : (n_years,) total radiative forcing [W/m^2]
    f_co2         : (n_years,) CO2 component of forcing [W/m^2]
    f_ex          : (n_years,) non-CO2 exogenous forcing [W/m^2]
    ecs_values    : (ensemble_size,) sampled ECS values used [degC]
    ensemble_size : actual number of members
    """

    def __init__(self, params: dict, n_years: int,
                 ensemble_size: int = None, seed: int = None):
        cp = params["climate"]
        ep = params.get("ensemble", {})

        # Resolve ensemble size
        if ensemble_size is None:
            ensemble_size = ep.get("size", 1)
        self.ensemble_size = max(1, int(ensemble_size))

        # Deterministic climate parameters (shared across ensemble members)
        self.eta         = cp["eta"]
        self.c1          = cp["c1"]
        self.c3          = cp["c3"]
        self.c4          = cp["c4"]
        self.f_ex_2015   = cp["f_ex_2015"]
        self.f_ex_2100   = cp["f_ex_2100"]
        self.m_at_pre    = params["carbon_cycle"]["m_at_preindustrial"]

        # ECS values — one per ensemble member
        self.ecs_values = self._sample_ecs(cp, ep, seed)
        self.lam_values = self.eta / self.ecs_values   # lambda(e) = eta/ECS(e)

        # State arrays: shape (n_years, ensemble_size)
        self.t_at    = np.zeros((n_years, self.ensemble_size))
        self.t_lo    = np.zeros((n_years, self.ensemble_size))

        # Forcing is scalar (does not depend on ECS): shape (n_years,)
        self.forcing = np.zeros(n_years)
        self.f_co2   = np.zeros(n_years)
        self.f_ex    = np.zeros(n_years)

        # Initial conditions: all ensemble members start from the same 2015 state
        self.t_at[0, :] = cp["t_at_2015"]
        self.t_lo[0, :] = cp["t_lo_2015"]

    # ------------------------------------------------------------------
    def _sample_ecs(self, cp: dict, ep: dict, seed) -> np.ndarray:
        """Sample ECS values for each ensemble member."""
        if self.ensemble_size == 1:
            return np.array([cp["ecs"]])

        _seed        = seed if seed is not None else ep.get("seed", 42)
        ecs_median   = ep.get("ecs_median",    3.0)
        sigma_log    = ep.get("ecs_sigma_log", 0.25)
        ecs_min      = ep.get("ecs_min",       1.5)
        ecs_max      = ep.get("ecs_max",       6.0)

        rng = np.random.default_rng(_seed)
        # Log-normal with given median: mu_log = ln(median)
        raw = rng.lognormal(np.log(ecs_median), sigma_log, self.ensemble_size)
        return np.clip(raw, ecs_min, ecs_max)

    # ------------------------------------------------------------------
    def step(self, t: int, m_at: float, elapsed: float):
        """
        Compute forcing and advance temperatures one timestep for all members.

        Radiative forcing is identical across ensemble members (it depends only
        on atmospheric CO2, which is the same for all members).  Temperature
        diverges because each member has a different ECS / lambda.

        Parameters
        ----------
        t       : timestep index
        m_at    : atmospheric carbon stock [GtC]
        elapsed : years since simulation start

        Returns
        -------
        t_at_mean : ensemble-mean surface temperature [degC]  — used for damage
        forcing   : total radiative forcing [W/m^2]
        """
        # CO2 radiative forcing (shared)
        self.f_co2[t] = self.eta * np.log2(max(m_at / self.m_at_pre, 1e-9))

        # Non-CO2 exogenous forcing ramp: linear 2015→2100, constant after
        frac = min(elapsed / 85.0, 1.0)
        self.f_ex[t]    = self.f_ex_2015 + (self.f_ex_2100 - self.f_ex_2015) * frac
        self.forcing[t] = self.f_co2[t] + self.f_ex[t]

        # 2-box temperature dynamics — vectorised over ensemble members
        # lam_values: (ensemble_size,);  t_at[t,:]: (ensemble_size,)
        if t < self.t_at.shape[0] - 1:
            self.t_at[t+1, :] = (
                self.t_at[t, :]
                + self.c1 * (self.forcing[t]
                             - self.lam_values * self.t_at[t, :]
                             - self.c3 * (self.t_at[t, :] - self.t_lo[t, :]))
            )
            self.t_lo[t+1, :] = (self.t_lo[t, :]
                                  + self.c4 * (self.t_at[t, :] - self.t_lo[t, :]))

        return float(self.t_at[t, :].mean()), self.forcing[t]

    # ------------------------------------------------------------------
    @property
    def t_at_mean(self) -> np.ndarray:
        """Ensemble mean surface temperature (n_years,)."""
        return self.t_at.mean(axis=1)

    @property
    def t_at_median(self) -> np.ndarray:
        """Ensemble median surface temperature (n_years,)."""
        return np.median(self.t_at, axis=1)

    def percentile(self, p: float) -> np.ndarray:
        """
        Return the p-th percentile of the ensemble temperature at each timestep.

        Parameters
        ----------
        p : percentile in [0, 100]

        Returns
        -------
        (n_years,) array
        """
        return np.percentile(self.t_at, p, axis=1)

    def equilibrium_temperature(self, forcing: float, member: int = 0) -> float:
        """Equilibrium T_AT for a sustained forcing for a given ensemble member."""
        return forcing / self.lam_values[member]

    def years_above_threshold(self, threshold_c: float, use_mean: bool = True) -> int:
        """
        Count timesteps where temperature exceeds a threshold.

        Parameters
        ----------
        threshold_c : temperature threshold [degC]
        use_mean    : if True, apply threshold to ensemble mean;
                      if False, return the median count across ensemble members.
        """
        if use_mean:
            return int(np.sum(self.t_at_mean > threshold_c))
        counts = np.sum(self.t_at > threshold_c, axis=0)
        return int(np.median(counts))
