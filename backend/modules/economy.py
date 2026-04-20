"""
Economy module — Neoclassical Cobb-Douglas regional economy.

Production function (Cobb-Douglas):
    Y_gross(r,t) = A(r,t) * K(r,t)^gamma * L(r,t)^(1-gamma)

where:
    A   = total factor productivity (TFP), grows exponentially then decelerates
    K   = capital stock, accumulates via savings net of depreciation
    L   = labor force (proxied by population), follows logistic growth to SSP ceiling

Net output after climate damage and abatement cost:
    Y_net = Y_gross * (1 - damage_fraction) * (1 - abatement_fraction)

Consumption and per-capita income are tracked for welfare analysis.

Units
-----
    GDP / output     : trillion 2015 USD / year
    Population       : billions
    Capital stock    : trillion 2015 USD
    GDP per capita   : thousand USD / person / year  (= trillion/billion)
"""

import numpy as np


class EconomyModule:
    """
    Regional neoclassical economy following the DICE/RICE50+ framework.

    Parameters
    ----------
    params   : full parameter dict loaded from params.json
    ssp_cfg  : SSP-specific sub-dict (pop_max, pop_speed, tfp_mult, sigma_mult)
    n_years  : number of simulation timesteps
    """

    def __init__(self, params: dict, ssp_cfg: dict, n_years: int,
                 economy_type: str = "market"):
        ic = params["initial_conditions"]
        ep = params["economy"]

        self.economy_type  = economy_type
        self.rho_ramsey   = 0.015   # pure rate of time preference for Ramsey rule

        # Production parameters
        self.gamma       = ep["capital_elasticity"]      # capital share (gamma ~ 0.3)
        self.delta_k     = ep["depreciation_rate"]       # annual depreciation rate
        self.tfp_growth_0 = np.array(ep["tfp_growth_0"]) # baseline TFP growth rates
        self.tfp_halving  = ep["tfp_halving_years"]      # growth halves every N years
        self.sigma_dec_0  = np.array(ep["sigma_decline_0"])  # autonomous decarbonisation

        # SSP-specific multipliers
        self.pop_max   = np.array(ssp_cfg["pop_max"])   # logistic ceiling (billions)
        self.pop_speed = ssp_cfg["pop_speed"]            # convergence speed
        self.tfp_mult  = ssp_cfg["tfp_mult"]             # scales TFP growth
        self.sig_mult  = ssp_cfg["sigma_mult"]           # scales sigma decline

        # Initial conditions
        gdp_0 = np.array(ic["gdp_2015"])
        pop_0 = np.array(ic["pop_2015"])
        self.savings_rate = np.array(ic["savings_rate"])

        n = len(gdp_0)
        self.n_regions = n
        self.n_years   = n_years

        # State arrays — shape (n_regions, n_years)
        self.pop            = np.zeros((n, n_years))
        self.K              = np.zeros((n, n_years))
        self.tfp            = np.zeros((n, n_years))
        self.sigma          = np.zeros((n, n_years))   # carbon intensity
        self.y_gross        = np.zeros((n, n_years))
        self.y_net          = np.zeros((n, n_years))
        self.consumption    = np.zeros((n, n_years))
        self.gdp_per_capita = np.zeros((n, n_years))   # thousand USD/person

        # Initialise t=0
        self.pop[:, 0]   = pop_0
        self.K[:, 0]     = gdp_0 * ic["capital_to_gdp_ratio"]
        self.sigma[:, 0] = np.array(ic["sigma_2015"])
        # Back-calculate TFP: A = Y / (K^gamma * L^(1-gamma))
        self.tfp[:, 0] = gdp_0 / (self.K[:, 0] ** self.gamma
                                    * pop_0 ** (1.0 - self.gamma))

    # ------------------------------------------------------------------
    def step_production(self, t: int, elapsed: float):
        """
        Advance population, TFP, carbon intensity, and gross output for timestep t.
        Call this before damage and abatement are known.

        Parameters
        ----------
        t       : timestep index (0-based)
        elapsed : years since simulation start

        Returns
        -------
        y_gross : (n_regions,) gross economic output [trillion USD/yr]
        sigma   : (n_regions,) carbon intensity [GtCO2/trillion USD]
        """
        if t > 0:
            # Population — logistic growth toward SSP-specific ceiling
            self.pop[:, t] = (self.pop[:, t-1]
                               + self.pop_speed * (self.pop_max - self.pop[:, t-1]))
            self.pop[:, t] = np.maximum(self.pop[:, t], 0.01)  # floor at 10 million

            # TFP — exponentially decelerating growth (economic convergence)
            g_a = self.tfp_growth_0 * self.tfp_mult * np.exp(-elapsed / self.tfp_halving)
            self.tfp[:, t] = self.tfp[:, t-1] * (1.0 + g_a)

            # Carbon intensity — autonomous decarbonisation (technology + structural change)
            self.sigma[:, t] = self.sigma[:, t-1] * (1.0 - self.sigma_dec_0 * self.sig_mult)

        # Gross output — Cobb-Douglas: Y = A * K^gamma * L^(1-gamma)
        self.y_gross[:, t] = (self.tfp[:, t]
                               * self.K[:, t] ** self.gamma
                               * self.pop[:, t] ** (1.0 - self.gamma))

        return self.y_gross[:, t].copy(), self.sigma[:, t].copy()

    def step_capital(self, t: int, damage_frac: float, abate_frac: np.ndarray):
        """
        Compute net output, consumption, per-capita income, and accumulate capital.
        Call after damage_frac and abate_frac are available for this timestep.

        Parameters
        ----------
        t           : timestep index
        damage_frac : scalar fraction of output lost to climate damage
        abate_frac  : (n_regions,) fraction of output spent on abatement
        """
        self.y_net[:, t] = (self.y_gross[:, t]
                             * (1.0 - damage_frac)
                             * (1.0 - abate_frac))

        # Savings rate: fixed (market) or Ramsey-optimal (social planner)
        if self.economy_type == "optimal":
            # Ramsey rule: savings rate converges from market rates toward s_golden
            # s_golden = γδ/(δ+ρ) — golden-rule savings under time preference ρ
            s_golden = self.gamma * self.delta_k / (self.delta_k + self.rho_ramsey)
            alpha = np.exp(-float(t) / 40.0)   # 40-year convergence half-life
            savings = s_golden + (self.savings_rate - s_golden) * alpha
        else:
            savings = self.savings_rate

        # Consumption = non-saved share of net output
        self.consumption[:, t] = (1.0 - savings) * self.y_net[:, t]

        # GDP per capita (trillion USD / billion = thousand USD/person)
        self.gdp_per_capita[:, t] = self.y_net[:, t] / self.pop[:, t]

        # Capital accumulation: K(t+1) = (1-delta)*K(t) + s*Y_net(t)
        if t < self.n_years - 1:
            self.K[:, t+1] = ((1.0 - self.delta_k) * self.K[:, t]
                               + savings * self.y_net[:, t])
