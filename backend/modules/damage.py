"""
Damage module considers climate damage or fraction of gross output lost to climate change (sea-level rise, extreme weather, health, agriculture…).
Damage Functions:
- Quadratic, DICE 2016R standard
- Linear, proportional damage
- Threshold, quadratic + extra penalty once temp passes critical threshold

Determines social cost of carbon (SCC), present marginal damage of one extra ton of CO2
"""

import numpy as np

class DamageModule:
    def __init__(self, params: dict):
        dp = params["damage"]
        self.damage_type = dp.get("damage_type", "quadratic")

        self.psi1 = dp.get("psi1", 0.0)
        self.psi2 = dp.get("psi2", 0.00267)
        self.threshold_temp = dp.get("threshold_temp", 3.0)
        self.threshold_damage = dp.get("threshold_damage", 0.05)

    # Calculate damage fraction at surface temperature anomaly above pre-indsutrial
    def calculate_damage_frac(self, t_at: float) -> float:
        if self.damage_type == "quadratic": omega = self.psi2 * t_at ** 2
        elif self.damage_type == "linear": omega = self.psi1 * t_at
        elif self.damage_type == "threshold":
            omega = self.psi2 * t_at ** 2
            if t_at >= self.threshold_temp:
                omega += self.threshold_damage * (t_at - self.threshold_temp)

        return float(np.clip(omega, 0.0, 0.99))

    # Marginal damage rate for SCC
    def d_omega_d_t(self, t_at: float) -> float:
        if self.damage_type == "quadratic": return 2.0 * self.psi2 * t_at
        elif self.damage_type == "linear": return self.psi1
        elif self.damage_type == "threshold":
            deriv = 2.0 * self.psi2 * t_at
            if t_at >= self.threshold_temp:
                deriv += self.threshold_damage
            return deriv

    def social_cost_of_carbon(self, t_at: float, y_gross_global: float, dt_per_gtco2: float = 5e-4) -> float:
        return float(self.d_omega_d_t(t_at) * dt_per_gtco2 * y_gross_global * 1e3)
