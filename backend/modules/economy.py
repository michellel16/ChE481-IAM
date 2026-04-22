"""
Economy module tracks GDP, capita, etc. and uses neoclassical Cobb-Douglas economy type
Cobb-Douglas: Y_gross(r,t) = A(r,t) * K(r,t)^gamma * L(r,t)^(1-gamma)
A is total factor productivity (TFP)
K is capital stock (accumulates via savings net of depreciation)
L is labor force (estimated by population), growth until SSP maximum

Net output after climate damage and abatement cost: Y_net = Y_gross * (1 - damage_fraction) * (1 - abatement_fraction)
"""

import numpy as np

class EconomyModule:
    def __init__(self, params: dict, ssp_cfg: dict, n_years: int, economy_type: str = "market"):
        ic = params["initial_conditions"]
        ep = params["economy"]

        self.economy_type = economy_type
        self.rho_ramsey = 0.015 # Pure rate of time preference for Ramsey rule

        self.gamma = ep["capital_elasticity"] # Capital share
        self.delta_k = ep["depreciation_rate"] # Annual depreciation rate
        self.tfp_growth_0 = np.array(ep["tfp_growth_0"]) # Baseline TFP growth rate
        self.tfp_halving = ep["tfp_halving_years"]
        self.sigma_dec_0 = np.array(ep["sigma_decline_0"]) # Decarbonization

        # SSP-specific - config
        self.pop_max = np.array(ssp_cfg["pop_max"]) # Maximum population growth
        self.pop_speed = ssp_cfg["pop_speed"]
        self.tfp_mult = ssp_cfg["tfp_mult"] # Scale of TFP growth
        self.sig_mult = ssp_cfg["sigma_mult"] # Scales of sigma decline

        # Initial GDP, population, savings rate
        gdp_0 = np.array(ic["gdp_2015"])
        pop_0 = np.array(ic["pop_2015"])
        self.savings_rate = np.array(ic["savings_rate"])

        n = len(gdp_0)
        self.n_regions = n
        self.n_years   = n_years

        self.pop  = np.zeros((n, n_years))
        self.K = np.zeros((n, n_years))
        self.tfp = np.zeros((n, n_years))
        self.sigma = np.zeros((n, n_years)) # Carbon intensity
        self.y_gross = np.zeros((n, n_years))
        self.y_net = np.zeros((n, n_years))
        self.consumption = np.zeros((n, n_years))
        self.gdp_per_capita = np.zeros((n, n_years))

        self.pop[:, 0] = pop_0
        self.K[:, 0] = gdp_0 * ic["capital_to_gdp_ratio"]
        self.sigma[:, 0] = np.array(ic["sigma_2015"])
        self.tfp[:, 0] = gdp_0 / (self.K[:, 0] ** self.gamma
                                    * pop_0 ** (1.0 - self.gamma))

    # Determine population growth, carbon intensity, TFP growth, gross economic output for damage and abatement modules
    def step_production(self, t: int, elapsed: float):
        if t > 0:
            self.pop[:, t] = (self.pop[:, t-1] + self.pop_speed * (self.pop_max - self.pop[:, t-1])) # Population growth toward SSP maximum
            self.pop[:, t] = np.maximum(self.pop[:, t], 0.01)

            g_a = self.tfp_growth_0 * self.tfp_mult * np.exp(-elapsed / self.tfp_halving) # TFP growth, exponentially decelerating
            self.tfp[:, t] = self.tfp[:, t-1] * (1.0 + g_a)

            self.sigma[:, t] = self.sigma[:, t-1] * (1.0 - self.sigma_dec_0 * self.sig_mult) # Carbon intensity w/ decarbonization (CDR)

        # Gross output using Cobb-Douglas
        self.y_gross[:, t] = (self.tfp[:, t] * self.K[:, t] ** self.gamma * self.pop[:, t] ** (1.0 - self.gamma))

        return self.y_gross[:, t].copy(), self.sigma[:, t].copy()

    # Determine net economic output, per-capita income, and capital accumulation for next time step after considering results from damage and abatmenet modules
    def step_capital(self, t: int, damage_frac: float, abate_frac: np.ndarray):
        # Net economic output
        self.y_net[:, t] = np.maximum(self.y_gross[:, t] * (1.0 - damage_frac) - self.y_gross[:, t] * abate_frac,0.0)

        # Savings rate, depends on fixed market or Ramsey-rule (optimal) -> savings rate converges from market rates toward s_golden
        if self.economy_type == "optimal":
            s_golden = self.gamma * self.delta_k / (self.delta_k + self.rho_ramsey)
            alpha = np.exp(-float(t) / 40.0)
            savings = s_golden + (self.savings_rate - s_golden) * alpha
        else:
            savings = self.savings_rate

        self.consumption[:, t] = (1.0 - savings) * self.y_net[:, t] # What's left after savings (damage and abatement)

        self.gdp_per_capita[:, t] = self.y_net[:, t] / self.pop[:, t]

        if t < self.n_years - 1: # Capital accumulation
            self.K[:, t+1] = ((1.0 - self.delta_k) * self.K[:, t] + savings * self.y_net[:, t])
