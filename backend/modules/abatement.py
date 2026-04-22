"""
Abatement module determines cost of emissions reduction as fraction of gross output using Marginal Abatement Cost (MAC) curve
At full decarbonization (emissions control rate is 1), marginal cost equals current backstop price

Marginal Abatement Cost (MAC) equals payback time (backstop price) multiplied by control rate, anchor for cost-curve
"""

import numpy as np

class AbatementModule:
    # Convex MAC curve, backstop price rate declining
    def __init__(self, params: dict):
        ap = params["abatement"]
        self.theta2 = ap["theta2"]
        self.pback = ap["pback"]
        self.gback = ap["gback"]
        self.pback_base_year = ap.get("pback_base_year", 2010)

    # Backstop price declining from start to end year
    def pback_time(self, elapsed: float, start_year: int = 2015) -> float:
        current_year = start_year + elapsed
        years_from_base = current_year - self.pback_base_year
        return self.pback * (1.0 - self.gback) ** years_from_base

    # Cost coefficient for MAC curve, based on regional carbon intensity and backstop price
    def cost_coeff(self, sigma: np.ndarray, elapsed: float, start_year: int = 2015) -> np.ndarray:
        return self.pback_time(elapsed, start_year) * sigma / self.theta2 / 1000.0

    # Abatement cost as fraction of gross output, based on emissions control rate and carbon intensity
    def compute(self, cr: np.ndarray, sigma: np.ndarray, elapsed: float, start_year: int = 2015) -> np.ndarray:
        cr_clipped = np.clip(cr, 0.0, 1.0)
        return self.cost_coeff(sigma, elapsed, start_year) * cr_clipped ** self.theta2

    # Regional marginal abatement cost as $/tCO2, based on emissions control rate and backstop price
    def marginal_abatement_cost(self, cr: np.ndarray, sigma: np.ndarray,
                                elapsed: float, start_year: int = 2015) -> np.ndarray:
        cr_safe = np.clip(cr, 1e-6, 1.0)
        return self.pback_time(elapsed, start_year) * cr_safe ** (self.theta2 - 1.0)
