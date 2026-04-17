"""
Carbon cycle module — 3-box atmosphere/ocean model (DICE 2016R).

Three reservoirs exchange carbon:
    M_AT  atmosphere            (Box 1)
    M_UP  upper ocean/biosphere (Box 2)
    M_LO  deep ocean            (Box 3)

Transition equations (annual timestep):
    M_AT(t+1) = E(t)*c + phi_11*M_AT(t) + phi_12*M_UP(t)
    M_UP(t+1) =          phi_21*M_AT(t) + phi_22*M_UP(t) + phi_23*M_LO(t)
    M_LO(t+1) =                           phi_32*M_UP(t) + phi_33*M_LO(t)

Transfer fractions satisfy mass balance:
    b21 = b12 * (M_AT_pre / M_UP_pre)
    b32 = b23 * (M_UP_pre / M_LO_pre)

CO2 concentration in ppm:
    ppm(t) = (M_AT(t) / M_AT_preindustrial) * ppm_preindustrial

Units: GtC for stocks; GtCO2/yr for emissions input.
"""

import numpy as np

_GTC_PER_GTCO2 = 12.0 / 44.0   # molecular weight ratio C/CO2


class CarbonCycleModule:
    """
    Three-reservoir carbon cycle model.

    Attributes (arrays of length n_years)
    ------
    m_at     : atmospheric carbon [GtC]
    m_up     : upper ocean/biosphere carbon [GtC]
    m_lo     : deep ocean carbon [GtC]
    co2_ppm  : atmospheric CO2 concentration [ppm]
    """

    def __init__(self, params: dict, n_years: int):
        cp = params["carbon_cycle"]

        self.m_at_pre  = cp["m_at_preindustrial"]
        self.m_up_pre  = cp["m_up_preindustrial"]
        self.m_lo_pre  = cp["m_lo_preindustrial"]
        self.ppm_pre   = cp["preindustrial_co2_ppm"]   # ~278 ppm

        b12 = cp["b12"]
        b23 = cp["b23"]
        b21 = b12 * (self.m_at_pre / self.m_up_pre)
        b32 = b23 * (self.m_up_pre / self.m_lo_pre)

        # Transition matrix (rows = destination box, cols = source box)
        self.phi = np.array([
            [1.0 - b12,          b21,          0.0      ],
            [b12,       1.0 - b21 - b23,        b32      ],
            [0.0,                b23,      1.0 - b32     ],
        ])

        # State arrays
        self.m_at    = np.zeros(n_years)
        self.m_up    = np.zeros(n_years)
        self.m_lo    = np.zeros(n_years)
        self.co2_ppm = np.zeros(n_years)

        # Initial conditions (2015)
        self.m_at[0]    = cp["m_at_2015"]
        self.m_up[0]    = cp["m_up_2015"]
        self.m_lo[0]    = cp["m_lo_2015"]
        self.co2_ppm[0] = self._to_ppm(self.m_at[0])

    # ------------------------------------------------------------------
    def step(self, t: int, global_emissions_gtco2: float):
        """
        Advance carbon cycle one year.

        Parameters
        ----------
        t                      : current timestep index
        global_emissions_gtco2 : total CO2 emitted this year [GtCO2/yr]

        Returns
        -------
        m_at    : atmospheric carbon stock this timestep [GtC]
        co2_ppm : atmospheric CO2 concentration this timestep [ppm]
        """
        e_gtc = global_emissions_gtco2 * _GTC_PER_GTCO2

        if t < len(self.m_at) - 1:
            state      = np.array([self.m_at[t], self.m_up[t], self.m_lo[t]])
            next_state = self.phi @ state + np.array([e_gtc, 0.0, 0.0])
            self.m_at[t+1] = next_state[0]
            self.m_up[t+1] = next_state[1]
            self.m_lo[t+1] = next_state[2]

        self.co2_ppm[t] = self._to_ppm(self.m_at[t])
        return self.m_at[t], self.co2_ppm[t]

    # ------------------------------------------------------------------
    def _to_ppm(self, m_at: float) -> float:
        """Convert atmospheric carbon (GtC) to CO2 concentration (ppm)."""
        return (m_at / self.m_at_pre) * self.ppm_pre

    def airborne_fraction(self, t: int, cumulative_emissions_gtc: float) -> float:
        """
        Fraction of cumulative emissions still in the atmosphere at timestep t.
        Useful as a model diagnostic.
        """
        if cumulative_emissions_gtc <= 0:
            return float("nan")
        delta_m_at = self.m_at[t] - self.m_at[0]
        return float(delta_m_at / cumulative_emissions_gtc)
