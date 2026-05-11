"""
Welfare module: social welfare functions under different distributive justice frameworks.

Adapted from JUSTICE model (Emmerling et al.) — see:
  Berger & Emmerling (2020), "Welfare as Equity Equivalents", J. Economic Surveys.

Frameworks
----------
utilitarian    — Benthamite sum of discounted isoelastic utilities. Neutral on inequality.
prioritarian   — Extra weight on worse-off regions (Rawls-inspired). High inequality aversion, zero PRTP.
sufficientarian — Applies a sufficiency floor (consumption threshold) before aggregating.
egalitarian    — Penalises inequality through a Gini weighting.

Each framework uses the equity-equivalent aggregation method from Berger & Emmerling:
  1. Transform consumption via isoelastic utility (inequality aversion parameter).
  2. Compute population-weighted sum across regions.
  3. Apply optional Gini penalty for egalitarian framework.
  4. Invert back to consumption-equivalent.
  5. Apply elasticity of marginal utility (elasmu) and temporal discounting (prstp).
"""

import numpy as np

_SMALL = 1e-9


def _utility(c: np.ndarray, eta: float) -> np.ndarray:
    """Isoelastic utility u(c) = c^(1-eta)/(1-eta), with log limit at eta=1."""
    c = np.maximum(c, _SMALL)
    if abs(eta - 1.0) < 1e-10:
        return np.log(c)
    return c ** (1.0 - eta) / (1.0 - eta)


def _inv_utility(u: np.ndarray, eta: float) -> np.ndarray:
    """Inverse isoelastic utility."""
    if abs(eta - 1.0) < 1e-10:
        return np.exp(u)
    return np.maximum(u * (1.0 - eta), _SMALL) ** (1.0 / (1.0 - eta))


def _gini_1d(x: np.ndarray) -> float:
    """Gini coefficient for a 1-D array (all non-negative)."""
    x = np.maximum(x, 0.0)
    if x.sum() < _SMALL:
        return 0.0
    x_sorted = np.sort(x)
    n = len(x_sorted)
    idx = np.arange(1, n + 1)
    return float((2.0 * np.dot(idx, x_sorted)) / (n * x_sorted.sum()) - (n + 1.0) / n)


_TYPE_DEFAULTS = {
    "utilitarian":    {"elasmu": 1.45, "prstp": 0.015, "inequality_aversion": 0.0,
                       "sufficiency_threshold": 0.0, "egality_strictness": 0.0},
    "prioritarian":   {"elasmu": 1.45, "prstp": 0.0,   "inequality_aversion": 2.0,
                       "sufficiency_threshold": 0.0, "egality_strictness": 0.0},
    "sufficientarian":{"elasmu": 1.45, "prstp": 0.015, "inequality_aversion": 0.0,
                       "sufficiency_threshold": 0.456, "egality_strictness": 0.0},
    "egalitarian":    {"elasmu": 1.45, "prstp": 0.0,   "inequality_aversion": 0.5,
                       "sufficiency_threshold": 0.0, "egality_strictness": 1.0},
}


class WelfareModule:
    """
    Computes aggregate social welfare across regions and time.

    Parameters
    ----------
    welfare_type : str
        One of 'utilitarian', 'prioritarian', 'sufficientarian', 'egalitarian'.
    params : dict
        IAM parameter dict containing a 'welfare' section with typed subsections.
    """

    def __init__(self, welfare_type: str, params: dict):
        wp = params.get("welfare", {})
        # Merge: built-in type defaults < top-level params < typed subsection
        base = _TYPE_DEFAULTS.get(welfare_type, _TYPE_DEFAULTS["utilitarian"]).copy()
        base["elasmu"] = wp.get("elasmu", base["elasmu"])
        base["prstp"] = wp.get("prstp", base["prstp"])
        cfg = wp.get(welfare_type, {})
        base.update(cfg)

        self.welfare_type = welfare_type
        self.elasmu = base["elasmu"]
        self.prstp = base["prstp"]
        self.inequality_aversion = base["inequality_aversion"]
        self.sufficiency_threshold = base["sufficiency_threshold"]
        self.egality_strictness = base["egality_strictness"]

    def compute(
        self,
        consumption_pc: np.ndarray,
        population: np.ndarray,
        years: np.ndarray,
    ) -> dict:
        """
        Compute welfare metrics over the simulation horizon.

        Parameters
        ----------
        consumption_pc : (n_regions, n_years) in trillion USD / person
        population     : (n_regions, n_years) in billions
        years          : (n_years,) calendar years

        Returns
        -------
        dict with keys:
          welfare              — scalar total welfare
          welfare_per_year     — (n_years,) discounted welfare at each step
          equity_equiv_consumption — (n_years,) region-aggregated consumption-equivalent
          discount_rate        — (n_years,) temporal discount weights
          gini_per_year        — (n_years,) Gini coefficient across regions
        """
        n_t = consumption_pc.shape[1]

        pop_total = population.sum(axis=0)  # (n_t,)
        pop_share = population / np.maximum(pop_total[None, :], _SMALL)  # (n_regions, n_t)

        # Sufficiency floor: shift consumption relative to threshold
        c = np.maximum(consumption_pc - self.sufficiency_threshold, _SMALL)

        # --- Spatial aggregation via equity-equivalent method ---
        ia = self.inequality_aversion

        # Step 1: transform via inequality-aversion utility
        u_ia = _utility(c, ia)  # (n_regions, n_t)

        # Step 2: population-weighted sum across regions
        weighted_sum = (pop_share * u_ia).sum(axis=0)  # (n_t,)

        # Step 3: always compute Gini (for display); apply penalty only if egality_strictness > 0
        gini_arr = np.array([_gini_1d(c[:, t]) for t in range(n_t)])
        if self.egality_strictness > 0.0:
            weighted_sum = weighted_sum * (1.0 - self.egality_strictness * gini_arr)

        # Step 4: invert back to consumption-equivalent
        c_eq = _inv_utility(weighted_sum, ia)  # (n_t,)

        # Step 5: marginal utility (elasmu) transform
        spatially_agg = _utility(c_eq, self.elasmu)  # (n_t,)

        # --- Temporal discounting ---
        t_idx = np.arange(n_t)
        discount = 1.0 / (1.0 + self.prstp) ** t_idx  # (n_t,)

        temporally_weighted = (spatially_agg - 1.0) * discount
        total_welfare = float(temporally_weighted.sum())

        return {
            "welfare": total_welfare,
            "welfare_per_year": temporally_weighted,
            "equity_equiv_consumption": c_eq,
            "discount_rate": discount,
            "gini_per_year": gini_arr,
        }

    def regional_welfare(
        self,
        consumption_pc: np.ndarray,
        years: np.ndarray,
    ) -> np.ndarray:
        """
        Per-region discounted welfare (n_regions,), ignoring spatial aggregation.
        Useful for identifying which regions gain/lose under a policy.
        """
        n_t = consumption_pc.shape[1]
        c = np.maximum(consumption_pc - self.sufficiency_threshold, _SMALL)

        u = _utility(c, self.elasmu)  # (n_regions, n_t)

        t_idx = np.arange(n_t)
        discount = 1.0 / (1.0 + self.prstp) ** t_idx

        return ((u - 1.0) * discount[None, :]).sum(axis=1)  # (n_regions,)
