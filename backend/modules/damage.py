"""
Damage module: climate damage as a fraction of gross output.
Reference for Kalkuhl: https://doi.org/10.1016/j.jeem.2019.102255
"""

import numpy as np


class KalkuhlDamage:
    _DEFAULTS = {
        "short_run_temp_change_coefficient": 0.00641,
        "lagged_short_run_temp_change_coefficient": 0.00345,
        "interaction_term_temp_change_coefficient": -0.00105,
        "lagged_interaction_term_temp_change_coefficient": -0.000718,
        "damage_gdp_ratio_with_gradient": 0.01,
        "temperature_difference_scaling_factor": 0.35,
        "damage_growth_rate": 4,
    }

    def __init__(self, kp: dict, timestep: int = 1):
        d = {**self._DEFAULTS, **kp}
        kw_DT = d["short_run_temp_change_coefficient"]
        kw_DT_lag = d["lagged_short_run_temp_change_coefficient"]
        kw_TDT = d["interaction_term_temp_change_coefficient"]
        kw_TDT_lag = d["lagged_interaction_term_temp_change_coefficient"]

        self.coeff_a = (kw_DT + kw_DT_lag) / timestep
        self.coeff_b = (kw_TDT + kw_TDT_lag) / timestep

        self.grad_ratio = d["damage_gdp_ratio_with_gradient"]
        self.grad_scale = d["temperature_difference_scaling_factor"]
        self.grad_power = d["damage_growth_rate"]

        self._dt = timestep
        self._t_prev = None
        self._damage_spec_prev = 0.0
        self._econ_damage_prev = 0.0

    def step(self, t_at: float) -> float:
        if self._t_prev is None:
            self._t_prev = t_at
            return 0.0

        dT = t_at - self._t_prev

        damage_spec = self.coeff_a * dT + self.coeff_b * dT * self._t_prev

        denom = (1.0 + self._damage_spec_prev) ** self._dt
        econ_damage = (1.0 + self._econ_damage_prev) / denom - 1.0

        unbounded = 1.0 - 1.0 / (1.0 + econ_damage)
        gradient = self.grad_ratio * abs(dT / self.grad_scale) ** self.grad_power

        total = float(np.clip(unbounded + gradient, 0.0, 0.99))

        self._t_prev = t_at
        self._damage_spec_prev = damage_spec
        self._econ_damage_prev = econ_damage

        return total

    def reset(self):
        self._t_prev = None
        self._damage_spec_prev = 0.0
        self._econ_damage_prev = 0.0

class DamageModule:
    def __init__(self, params: dict):
        dp = params["damage"]
        self.damage_type = dp.get("type", dp.get("damage_type", "quadratic"))

        quad = dp.get("quadratic", dp)
        thresh = dp.get("threshold", dp)
        self.psi1 = quad.get("psi1", dp.get("psi1", 0.0))
        self.psi2 = quad.get("psi2", dp.get("psi2", 0.00267))
        self.threshold_temp = thresh.get("threshold_temp", dp.get("threshold_temp", 3.0))
        self.threshold_damage = thresh.get("threshold_damage", dp.get("threshold_damage", 0.05))

        kp = dp.get("kalkuhl", {})
        if self.damage_type == "kalkuhl":
            self._kalkuhl = KalkuhlDamage(kp, timestep=1)
        else:
            self._kalkuhl = None

    def calculate_damage_frac(self, t_at: float) -> float:
        if self.damage_type == "quadratic":
            omega = self.psi2 * t_at ** 2
        elif self.damage_type == "linear":
            omega = self.psi1 * t_at
        elif self.damage_type == "threshold":
            omega = self.psi2 * t_at ** 2
            if t_at >= self.threshold_temp:
                omega += self.threshold_damage * (t_at - self.threshold_temp)
        elif self.damage_type == "kalkuhl":
            return self._kalkuhl.step(t_at)
        else:
            omega = self.psi2 * t_at ** 2

        return float(np.clip(omega, 0.0, 0.99))

    def d_omega_d_t(self, t_at: float) -> float:
        if self.damage_type == "quadratic":
            return 2.0 * self.psi2 * t_at
        elif self.damage_type == "linear":
            return self.psi1
        elif self.damage_type == "threshold":
            deriv = 2.0 * self.psi2 * t_at
            if t_at >= self.threshold_temp:
                deriv += self.threshold_damage
            return deriv
        elif self.damage_type == "kalkuhl":
            return 2.0 * self.psi2 * t_at
        return 2.0 * self.psi2 * t_at

    def social_cost_of_carbon(self, t_at: float, y_gross_global: float,
                              dt_per_gtco2: float = 5e-4) -> float:
        return float(self.d_omega_d_t(t_at) * dt_per_gtco2 * y_gross_global * 1e3)
