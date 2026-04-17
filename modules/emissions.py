"""
Emissions module — converts economic output to CO2 emissions.

Total regional emissions have two components:

  1. Energy & industrial CO2 (endogenous):
        E_EI(r,t) = sigma(r,t) * [1 - mu(r,t)] * Y_gross(r,t)

     where sigma is carbon intensity [GtCO2/trillion USD] and mu is the
     emission control rate (fraction of unabated emissions avoided).

  2. Land-use change CO2 (exogenous):
        E_LU(t) = global trajectory declining linearly 2015 -> 2100,
                  then spread uniformly across regions.

Global total:
        E_global(t) = sum_r E_EI(r,t) + E_LU(t)

Units: GtCO2 / year
"""

import numpy as np


class EmissionsModule:
    """
    Regional CO2 emissions from energy/industry plus land-use change.

    Parameters
    ----------
    params    : full parameter dict from params.json
    n_regions : number of model regions
    n_years   : number of simulation timesteps
    """

    def __init__(self, params: dict, n_regions: int, n_years: int):
        ep = params["emissions"]
        self.land_2015    = ep["land_use_2015_gtco2"]
        self.land_2100    = ep["land_use_2100_gtco2"]
        self.n_regions    = n_regions
        self.n_years      = n_years

        # Output arrays
        self.emissions       = np.zeros((n_regions, n_years))  # GtCO2/yr per region
        self.emissions_ei    = np.zeros((n_regions, n_years))  # energy+industry only
        self.land_emissions  = np.zeros(n_years)               # global land-use GtCO2/yr

    # ------------------------------------------------------------------
    def step(self, t: int, elapsed: float, sim_length: float,
             y_gross: np.ndarray, sigma: np.ndarray, mu: np.ndarray):
        """
        Compute regional emissions for timestep t.

        Parameters
        ----------
        t          : timestep index
        elapsed    : years since start (for land-use interpolation)
        sim_length : total simulation years (denom for land-use ramp)
        y_gross    : (n_regions,) gross output [trillion USD/yr]
        sigma      : (n_regions,) carbon intensity [GtCO2/trillion USD]
        mu         : (n_regions,) emission control rate [0, 1]

        Returns
        -------
        regional_emissions : (n_regions,)   GtCO2/yr
        global_emissions   : float           GtCO2/yr
        """
        # Energy & industrial CO2
        self.emissions_ei[:, t] = sigma * (1.0 - np.clip(mu, 0.0, 1.0)) * y_gross

        # Land-use change — global, linearly declining 2015 → 2100
        frac = min(elapsed / max(sim_length, 1.0), 1.0)
        self.land_emissions[t] = self.land_2015 + (self.land_2100 - self.land_2015) * frac

        # Add land-use share to each region (uniform distribution)
        self.emissions[:, t] = (self.emissions_ei[:, t]
                                 + self.land_emissions[t] / self.n_regions)

        return self.emissions[:, t].copy(), float(self.emissions[:, t].sum())
