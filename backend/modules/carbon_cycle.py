"""
Carbon cycle module uses a 3 reservoir atmospheric/ocean model to model transfer/mixing of emissions
Three reservoirs: atmosphere, upper ocean/biosphere, deep ocean
- Carbon flows in both directions between adjacent reservoirs, mixing between depe ocean and oter reservoirs is slow

Model is limited, does not accurately represent ocean chemistry and carbon absorption (overpredicts atmospheric absorption for historical period)
"""

import numpy as np

CMW_PER_CO2MW = 12.0 / 44.0 # MW ratio C:CO2

class CarbonCycleModule:
    def __init__(self, params: dict, n_years: int):
        cp = params["carbon_cycle"]

        self.m_at_pre = cp["m_at_preindustrial"]
        self.m_up_pre = cp["m_up_preindustrial"]
        self.m_lo_pre = cp["m_lo_preindustrial"]
        self.ppm_pre = cp["preindustrial_co2_ppm"] # ~278 ppm

        b12 = cp["b12"]
        b23 = cp["b23"]
        b21 = b12 * (self.m_at_pre / self.m_up_pre)
        b32 = b23 * (self.m_up_pre / self.m_lo_pre)

        self.phi = np.array([
            [1.0 - b12, b21, 0.0],
            [b12, 1.0 - b21 - b23, b32],
            [0.0, b23, 1.0 - b32],
        ])

        self.m_at = np.zeros(n_years)
        self.m_up = np.zeros(n_years)
        self.m_lo = np.zeros(n_years)
        self.co2_ppm = np.zeros(n_years)

        # Initial conditions at 2015 start year
        self.m_at[0] = cp["m_at_2015"]
        self.m_up[0] = cp["m_up_2015"]
        self.m_lo[0] = cp["m_lo_2015"]
        self.co2_ppm[0] = self._to_ppm(self.m_at[0])

    # Carbon cycle per time step, atmospheric CO2 concentration and carbon stock
    def step(self, t: int, global_emissions_gtco2: float):
        e_gtc = global_emissions_gtco2 * CMW_PER_CO2MW

        if t < len(self.m_at) - 1:
            state = np.array([self.m_at[t], self.m_up[t], self.m_lo[t]])
            next_state = self.phi @ state + np.array([e_gtc, 0.0, 0.0])
            self.m_at[t + 1] = next_state[0]
            self.m_up[t + 1] = next_state[1]
            self.m_lo[t + 1] = next_state[2]

        self.co2_ppm[t] = self._to_ppm(self.m_at[t])
        return self.m_at[t], self.co2_ppm[t]

    # Convert atmospheric CO2 to CO2 conc
    def _to_ppm(self, m_at: float) -> float:
        return (m_at / self.m_at_pre) * self.ppm_pre

    # Determine frac of emissions still in atmosphere during time step
    def airborne_fraction(self, t: int, cumulative_emissions_gtc: float) -> float:
        if cumulative_emissions_gtc <= 0:
            return float("nan")
        delta_m_at = self.m_at[t] - self.m_at[0]
        return float(delta_m_at / cumulative_emissions_gtc)
