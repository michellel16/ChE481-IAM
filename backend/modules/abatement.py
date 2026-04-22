"""
Abatement module — DICE 2013R backstop-price MAC curve.

Cost of emissions reduction as a fraction of gross output (Eq. 6):

    Lambda(r,t) = cost1(r,t) * cr(r,t)^theta2

where the cost coefficient (Eq. 6 / GAMS cost1) is:

    cost1(r,t) = pback_time(t) * sigma(r,t) / theta2 / 1000

    pback_time(t) = pback * (1 - gback)^(year - base_year)   [$/tCO2]

This ensures that at full decarbonisation (cr=1) the marginal cost equals the
current backstop price.  The factor sigma * pback / 1000 converts $/tCO2 times
GtCO2/trillion_USD into a dimensionless fraction of GDP.

Marginal Abatement Cost (MAC) in USD/tCO2 (GAMS mcabateeq):

    MAC(r,t) = pback_time(t) * cr(r,t)^(theta2 - 1)

At cr = 1 this equals pback_time (the current backstop price), providing a
natural anchor for the cost curve.

FIX THIS
"""

import numpy as np


class AbatementModule:
    """
    Convex marginal abatement cost curve — DICE 2013R parameterisation.

    Parameters
    ----------
    params : full parameter dict from params.json
             theta2         : exponent of control cost function (DICE: 2.8)
             pback          : backstop cost in 2010 [$/tCO2]
             gback          : annual fractional decline in backstop price
             pback_base_year: reference year for pback (2010 in DICE 2013R)
    """

    def __init__(self, params: dict):
        ap = params["abatement"]
        self.theta2         = ap["theta2"]
        self.pback          = ap["pback"]
        self.gback          = ap["gback"]
        self.pback_base_year = ap.get("pback_base_year", 2010)

    # ------------------------------------------------------------------
    def pback_time(self, elapsed: float, start_year: int = 2015) -> float:
        """
        Backstop price at elapsed years from simulation start [$/tCO2].

        pback_time = pback * (1 - gback)^(current_year - base_year)
        """
        current_year = start_year + elapsed
        years_from_base = current_year - self.pback_base_year
        return self.pback * (1.0 - self.gback) ** years_from_base

    def cost1(self, sigma: np.ndarray, elapsed: float,
              start_year: int = 2015) -> np.ndarray:
        """
        Per-region cost coefficient (dimensionless fraction of GDP at cr=1).

        cost1(r,t) = pback_time(t) * sigma(r,t) / theta2 / 1000
        """
        return self.pback_time(elapsed, start_year) * sigma / self.theta2 / 1000.0

    def compute(self, cr: np.ndarray, sigma: np.ndarray,
                elapsed: float, start_year: int = 2015) -> np.ndarray:
        """
        Abatement cost as a fraction of gross output for each region.

        Lambda(r,t) = cost1(r,t) * cr(r,t)^theta2

        Parameters
        ----------
        cr         : (n_regions,) emission control rates in [0, 1]
        sigma      : (n_regions,) carbon intensity [GtCO2 / trillion USD]
        elapsed    : years since simulation start
        start_year : simulation start year (default 2015)

        Returns
        -------
        abate_frac : (n_regions,) cost as fraction of gross output
        """
        cr_clipped = np.clip(cr, 0.0, 1.0)
        return self.cost1(sigma, elapsed, start_year) * cr_clipped ** self.theta2

    def marginal_abatement_cost(self, cr: np.ndarray, sigma: np.ndarray,
                                 elapsed: float, start_year: int = 2015) -> np.ndarray:
        """
        Marginal abatement cost [$/tCO2] — GAMS mcabateeq:

            MAC(r,t) = pback_time(t) * cr(r,t)^(theta2 - 1)

        At cr = 1 this equals the current backstop price.

        Parameters
        ----------
        cr         : (n_regions,) emission control rate
        sigma      : (n_regions,) carbon intensity [GtCO2 / trillion USD]
                     (kept for API compatibility; not used in this formula)
        elapsed    : years since simulation start
        start_year : simulation start year

        Returns
        -------
        mac : (n_regions,) marginal abatement cost [USD / tCO2]
        """
        cr_safe = np.clip(cr, 1e-6, 1.0)
        return self.pback_time(elapsed, start_year) * cr_safe ** (self.theta2 - 1.0)
