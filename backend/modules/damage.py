"""
Damage module — fraction of gross output lost to climate change.

Climate damage Omega represents the share of economic output destroyed
by climate impacts (sea-level rise, extreme weather, health, agriculture…).

Three functional forms are supported (select via params.json "damage_type"):

  'quadratic'  — DICE 2016R standard:
                     Omega = psi2 * T^2

  'linear'     — simple proportional damage:
                     Omega = psi1 * T

  'threshold'  — quadratic plus an additional penalty once temperature
                 exceeds a critical threshold (models tipping-point risk):
                     Omega = psi2*T^2 + max(0, threshold_damage*(T - T_crit))

All functions return Omega in [0, 1), the fraction of gross output lost.

Social Cost of Carbon
---------------------
An approximate SCC [USD/tCO2] is provided as a diagnostic. It estimates
the present-period marginal damage of one extra tonne of CO2 as:

    SCC ≈ (dOmega/dT) * (dT/dE) * Y_gross_global * unit_conversion

where dT/dE is a rough marginal temperature response per GtCO2 emitted
(default 5e-4 degC/GtCO2, a first-order sensitivity estimate).  The full
DICE SCC integrates future discounted damages — this is a simplified proxy.
"""

import numpy as np


class DamageModule:
    """
    Climate damage function: maps temperature to fraction of output lost.

    Parameters
    ----------
    params : full parameter dict from params.json
             damage_type  : 'quadratic' | 'linear' | 'threshold'
             psi1         : linear coefficient  [degC^-1]
             psi2         : quadratic coefficient [degC^-2]
             threshold_temp   : temperature threshold for extra damage [degC]
             threshold_damage : additional damage rate above threshold [degC^-1]
    """

    _VALID = ("quadratic", "linear", "threshold")

    def __init__(self, params: dict):
        dp = params["damage"]
        self.damage_type      = dp.get("damage_type", "quadratic")
        if self.damage_type not in self._VALID:
            raise ValueError(f"damage_type must be one of {self._VALID}")

        self.psi1             = dp.get("psi1", 0.0)
        self.psi2             = dp.get("psi2", 0.00267)
        self.threshold_temp   = dp.get("threshold_temp", 3.0)
        self.threshold_damage = dp.get("threshold_damage", 0.05)

    # ------------------------------------------------------------------
    def compute(self, t_at: float) -> float:
        """
        Compute damage fraction Omega at surface temperature t_at.

        Parameters
        ----------
        t_at : temperature anomaly above pre-industrial [degC]

        Returns
        -------
        omega : damage fraction in [0, 0.99]
        """
        if self.damage_type == "quadratic":
            omega = self.psi2 * t_at ** 2

        elif self.damage_type == "linear":
            omega = self.psi1 * t_at

        elif self.damage_type == "threshold":
            omega = self.psi2 * t_at ** 2
            if t_at >= self.threshold_temp:
                omega += self.threshold_damage * (t_at - self.threshold_temp)

        return float(np.clip(omega, 0.0, 0.99))

    def d_omega_d_t(self, t_at: float) -> float:
        """Marginal damage rate dOmega/dT [degC^-1], used in SCC calculation."""
        if self.damage_type == "quadratic":
            return 2.0 * self.psi2 * t_at
        elif self.damage_type == "linear":
            return self.psi1
        elif self.damage_type == "threshold":
            deriv = 2.0 * self.psi2 * t_at
            if t_at >= self.threshold_temp:
                deriv += self.threshold_damage
            return deriv

    # ------------------------------------------------------------------
    def social_cost_of_carbon(self, t_at: float, y_gross_global: float,
                               dt_per_gtco2: float = 5e-4) -> float:
        """
        Approximate Social Cost of Carbon [USD / tCO2].

        SCC ≈ (dOmega/dT) * dt_per_gtco2 * Y_gross_global * 1e3

        Unit derivation:
            [1/degC] * [degC/GtCO2] * [trillion USD] * (1e12 USD/trillion) / (1e9 tCO2/GtCO2)
            = [1/GtCO2] * [trillion USD] * 1e3  →  USD/tCO2

        Parameters
        ----------
        t_at           : current temperature anomaly [degC]
        y_gross_global : sum of regional gross output [trillion USD/yr]
        dt_per_gtco2   : marginal temperature response [degC / GtCO2]

        Returns
        -------
        scc : USD / tCO2
        """
        return float(self.d_omega_d_t(t_at) * dt_per_gtco2 * y_gross_global * 1e3)
