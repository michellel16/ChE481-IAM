"""
Emissions module converts economic output to CO2 emissions where global emissions considers:
- Emissions from energy & industrial CO2: E_EI(r,t) = sigma(r,t) * [1 - cr(r,t)] * Y_gross(r,t)
sigma is carbon intensity (GtCO2/trillion USD), cr is emission control rate (fraction of unabated emissions avoided)

- Emissions from land-use change: E_LU(t) = global trajectory declining linearly over years before distributed evenly across regions.

Global Total: E_global(t) = sum_r E_EI(r,t) + E_LU(t)
"""

import numpy as np

class EmissionsModule:
    def __init__(self, params: dict, n_regions: int, n_years: int):
        ep = params["emissions"]
        self.land_2015 = ep["land_use_2015_gtco2"]
        self.land_2100 = ep["land_use_2100_gtco2"]
        self.n_regions = n_regions
        self.n_years = n_years

        self.emissions = np.zeros((n_regions, n_years)) # Initial GtCO2/yr per region
        self.emissions_ei = np.zeros((n_regions, n_years)) # Initial emissions from energy + industry
        self.land_emissions = np.zeros(n_years) # Initial global land-use GtCO2/yr

    def step(self, t: int, elapsed: float, sim_length: float,
             y_gross: np.ndarray, sigma: np.ndarray, cr: np.ndarray):

        # Regional energy & industrial emissions
        self.emissions_ei[:, t] = sigma * (1.0 - np.clip(cr, 0.0, 1.0)) * y_gross

        # Land-use change (global,linearly declining)
        frac = min(elapsed / max(sim_length, 1.0), 1.0)
        self.land_emissions[t] = self.land_2015 + (self.land_2100 - self.land_2015) * frac

        # Add land-use share to each region (equal distribution)
        self.emissions[:, t] = (self.emissions_ei[:, t]
                                 + self.land_emissions[t] / self.n_regions)

        return self.emissions[:, t].copy(), float(self.emissions[:, t].sum())
