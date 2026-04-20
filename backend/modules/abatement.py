"""
Abatement module — cost of reducing CO2 emissions (DICE 2016R framework).

Abatement cost as a fraction of gross output follows a convex MAC curve:

    Lambda(r,t) = theta1(t) * mu(r,t)^theta2

where:
    mu         : emission control rate in [0, 1]   (the policy lever)
    theta1(t)  : cost coefficient, declining over time with technology learning
    theta2     : exponent > 1, giving a convex (increasing marginal cost) curve
    theta1(t)  = theta1_0 * exp(-theta1_decay * elapsed_years)

Marginal Abatement Cost (MAC) in USD/tCO2:
    MAC(r,t) = d(Lambda*Y_gross)/d(E_reduced)
             = theta1(t) * theta2 * mu^(theta2-1) / sigma * 1e3

    where the factor 1e3 converts trillion USD/GtCO2 -> USD/tCO2.

The MAC curve rises steeply as mu approaches 1.0 (full decarbonisation),
reflecting the increasing cost of eliminating the last hard-to-abate emissions.
Technology learning (theta1 declining over time) shifts the curve downward,
representing cost reductions from R&D, economies of scale, and deployment.
"""

import numpy as np


class AbatementModule:
    """
    Convex marginal abatement cost curve with technology learning.

    Parameters
    ----------
    params : full parameter dict from params.json
             theta1_0     : initial cost coefficient at mu=1 (fraction of GDP)
             theta2       : exponent controlling curve convexity (DICE: 2.8)
             theta1_decay : annual fractional decline in theta1 (learning rate)
    """

    def __init__(self, params: dict):
        ap = params["abatement"]
        self.theta1_0    = ap["theta1_0"]
        self.theta2      = ap["theta2"]
        self.theta1_decay = ap["theta1_decay"]

    # ------------------------------------------------------------------
    def theta1(self, elapsed: float) -> float:
        """
        Cost coefficient at elapsed years.
        Declines exponentially: theta1(t) = theta1_0 * exp(-decay * t)
        """
        return self.theta1_0 * np.exp(-self.theta1_decay * elapsed)

    def compute(self, mu: np.ndarray, elapsed: float) -> np.ndarray:
        """
        Abatement cost as a fraction of gross output for each region.

        Parameters
        ----------
        mu      : (n_regions,) emission control rates in [0, 1]
        elapsed : years since simulation start

        Returns
        -------
        abate_frac : (n_regions,) cost as fraction of gross output
        """
        mu_clipped = np.clip(mu, 0.0, 1.0)
        return self.theta1(elapsed) * mu_clipped ** self.theta2

    def marginal_abatement_cost(self, mu: np.ndarray, sigma: np.ndarray,
                                 elapsed: float) -> np.ndarray:
        """
        Marginal abatement cost (MAC) in USD per tCO2.

        Derived as: MAC = d(Lambda)/d(mu) / sigma * 1e3
                        = theta1(t) * theta2 * mu^(theta2-1) / sigma * 1e3

        Parameters
        ----------
        mu      : (n_regions,) emission control rate
        sigma   : (n_regions,) carbon intensity [GtCO2 / trillion USD]
        elapsed : years since simulation start

        Returns
        -------
        mac : (n_regions,) marginal abatement cost [USD / tCO2]
        """
        mu_safe = np.clip(mu, 1e-6, 1.0)
        sigma_safe = np.maximum(sigma, 1e-9)
        mac_trillion_per_gtco2 = (self.theta1(elapsed)
                                   * self.theta2
                                   * mu_safe ** (self.theta2 - 1.0)
                                   / sigma_safe)
        # trillion USD / GtCO2 * (1e12 / 1e9) = 1e3 USD/tCO2
        return mac_trillion_per_gtco2 * 1e3

    def cost_at_target(self, mu_target: float, sigma_mean: float,
                        elapsed: float, y_gross_global: float) -> dict:
        """
        Summary cost metrics for reaching a uniform emission control target.

        Parameters
        ----------
        mu_target      : target emission control rate [0, 1]
        sigma_mean     : mean carbon intensity across regions [GtCO2/trillion USD]
        elapsed        : years since start
        y_gross_global : global gross output [trillion USD/yr]

        Returns
        -------
        dict with 'abatement_cost_frac', 'abatement_cost_trillion_usd',
                  'mac_usd_per_tco2', 'theta1_current'
        """
        frac = float(self.theta1(elapsed) * np.clip(mu_target, 0.0, 1.0) ** self.theta2)
        cost_tril = frac * y_gross_global
        mac = float(self.theta1(elapsed) * self.theta2
                    * max(mu_target, 1e-6) ** (self.theta2 - 1.0)
                    / max(sigma_mean, 1e-9) * 1e3)
        return {
            "abatement_cost_frac":         frac,
            "abatement_cost_trillion_usd": cost_tril,
            "mac_usd_per_tco2":            mac,
            "theta1_current":              self.theta1(elapsed),
        }
