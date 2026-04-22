"""
Emissions module — converts economic output to CO2 emissions.

Total regional emissions have two components:

  1. Energy & industrial CO2 (endogenous):
        E_EI(r,t) = sigma(r,t) * [1 - cr(r,t)] * Y_gross(r,t)

     where sigma is carbon intensity [GtCO2/trillion USD] and cr is the
     emission control rate (fraction of unabated emissions avoided).

  2. Land-use change CO2 (exogenous):
        E_LU(t) = global trajectory declining linearly 2015 -> 2100,
                  then spread uniformly across regions.

Global total:
        E_global(t) = sum_r E_EI(r,t) + E_LU(t)

Units: GtCO2 / year

FIX THIS
"""

import numpy as np

class EmissionsModule:
    def __init__(self, params: dict, n_regions: int, n_years: int):
        ep = params["emissions"]
        self.land_2015 = ep["land_use_2015_gtco2"]
        self.land_2100 = ep["land_use_2100_gtco2"]
        self.n_regions = n_regions
        self.n_years = n_years

        self.emissions = np.zeros((n_regions, n_years)) # initial GtCO2/yr per region
        self.emissions_ei = np.zeros((n_regions, n_years)) # initial emissions from energy + industry only
        self.land_emissions = np.zeros(n_years) # initial global land-use GtCO2/yr

    def step(self, t: int, elapsed: float, sim_length: float,
             y_gross: np.ndarray, sigma: np.ndarray, cr: np.ndarray):

        # Regional energy & industrial emissions
        self.emissions_ei[:, t] = sigma * (1.0 - np.clip(cr, 0.0, 1.0)) * y_gross

        # Land-use change (global,linearly declining)
        frac = min(elapsed / max(sim_length, 1.0), 1.0)
        self.land_emissions[t] = self.land_2015 + (self.land_2100 - self.land_2015) * frac

        # Add land-use share to each region (uniform distribution)
        self.emissions[:, t] = (self.emissions_ei[:, t]
                                 + self.land_emissions[t] / self.n_regions)

        return self.emissions[:, t].copy(), float(self.emissions[:, t].sum())
