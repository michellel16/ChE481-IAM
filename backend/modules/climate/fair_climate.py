"""
FaIR v2-based climate module: https://github.com/OMS-NetZero/FAIR/tree/master/src/fair

Differences from 2-box DICE model:
  - Multi-gas CO2-equivalent forcing (CO2, CH4, N2O, aerosols, …)
  - Impulse-response carbon cycle instead of 3-reservoir DICE model
  - 1001-member constrained ensemble from Cummins et al. calibration
  - Runs step-by-step at annual resolution, taking CO2 FFI emissions as input

Data requirements
-----------------
This module needs four files that can be downloaded from the JUSTICE project
(PythonProject3/JUSTICE) or fetched via the download helper below:
  - calibrated_constrained_parameters.csv
  - species_configs_properties_calibration.csv
  - rcmip_emissions_annual.csv
  - rcmip_concentrations_annual.csv
  - rcmip_forcing_annual.csv

Run `python -m backend.modules.climate.fair_climate --download` to fetch them.

Smith et al. (2021) FaIR v2. https://doi.org/10.5194/gmd-14-3007-2021
JUSTICE model: https://github.com/JEME-ICL/JUSTICE (CoupledFAIR)
"""

import os
import sys
import warnings
import copy
import numpy as np

try:
    import pandas as pd
    from scipy.interpolate import interp1d
    from fair import FAIR
    from fair.interface import fill, initialise
    from fair.io import read_properties
    from fair.forcing.ghg import meinshausen2020
    from fair.energy_balance_model import step_temperature, calculate_toa_imbalance_postrun
    from fair.earth_params import earth_radius, seconds_per_year
    from fair.gas_cycle import calculate_alpha
    from fair.gas_cycle.ch4_lifetime import calculate_alpha_ch4
    from fair.gas_cycle.eesc import calculate_eesc
    from fair.gas_cycle.forward import step_concentration
    from fair.gas_cycle.inverse import unstep_concentration
    from fair.forcing.aerosol.erfaci import logsum
    from fair.forcing.aerosol.erfari import calculate_erfari_forcing
    from fair.forcing.minor import calculate_linear_forcing
    from fair.forcing.ozone import thornhill2021
    from fair.constants import SPECIES_AXIS, TIME_AXIS
    from fair.structure.units import (
        compound_convert, desired_concentration_units, desired_emissions_units,
        mixing_ratio_convert, prefix_convert, time_convert,
    )
    FAIR_AVAILABLE = True
except ImportError:
    FAIR_AVAILABLE = False
    class FAIR:
        pass

_FAIR_START_YEAR = 1750
_SUPPRESS_WARNINGS = True

_SSP_MAP = {
    "ssp119": "ssp119", "ssp126": "ssp126", "ssp245": "ssp245",
    "ssp370": "ssp370", "ssp434": "ssp434", "ssp460": "ssp460",
    "ssp585": "ssp585",
    "SSP1": "ssp126", "SSP2": "ssp245", "SSP3": "ssp370",
    "SSP4": "ssp460", "SSP5": "ssp585",
    "SSP1-2.6": "ssp126", "SSP2-4.5": "ssp245", "SSP3-7.0": "ssp370",
    "SSP4-6.0": "ssp460", "SSP5-8.5": "ssp585",
}

def _find_fair_data_path(hint: str = None) -> str | None:
    candidates = []
    if hint:
        candidates.append(hint)

    here = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.normpath(os.path.join(here, "..", "..", "data", "fair_input")))

    for levels_up in range(3, 7):
        parent = here
        for _ in range(levels_up):
            parent = os.path.dirname(parent)
        justice_path = os.path.join(parent, "PythonProject3", "JUSTICE", "data", "input")
        candidates.append(os.path.normpath(justice_path))

    marker = "calibrated_constrained_parameters.csv"
    for path in candidates:
        if os.path.isfile(os.path.join(path, marker)):
            return path
    return None


class FAIRClimateModule(FAIR):
    def __init__(
        self,
        params: dict,
        n_years: int,
        start_year: int = 2015,
        scenario: str = "ssp245",
        ensemble_size: int = 1,
        seed: int = 42,
        data_path: str = None,
    ):
        if not FAIR_AVAILABLE:
            raise ImportError(
                "The 'fair' package is required for FAIRClimateModule.\n"
                "Install it with:  pip install fair\n"
                "Also install:     pip install pandas scipy"
            )

        super().__init__()

        fair_cfg = params.get("climate", {}).get("fair", {})
        scenario = _SSP_MAP.get(
            fair_cfg.get("scenario", scenario), fair_cfg.get("scenario", scenario)
        )
        ensemble_size = int(fair_cfg.get("ensemble_size", ensemble_size))
        data_hint = fair_cfg.get("data_path") or data_path

        self._iam_start_year = start_year
        self._iam_n_years = n_years
        self._iam_end_year = start_year + n_years - 1
        self.ensemble_size = ensemble_size

        self.t_at = np.zeros((n_years, ensemble_size))
        self.t_lo = np.zeros((n_years, ensemble_size))
        self.f_co2 = np.zeros(n_years)
        self.f_ex = np.zeros(n_years)
        self._m_at_out = np.zeros(n_years)   # atmospheric carbon (GtC) from FAIR
        self._co2_ppm_out = np.zeros(n_years)

        self._data_path = _find_fair_data_path(data_hint)
        if self._data_path is None:
            raise FileNotFoundError(
                "FAIR data files not found. Run the download helper:\n"
                "  python -m backend.modules.climate.fair_climate --download\n"
                "or copy them from the JUSTICE project's data/input/ folder."
            )

        self._initialize_fair(scenario, ensemble_size)
        self.forcing = np.zeros(n_years)

    def _initialize_fair(self, scenario: str, ensemble_size: int):
        self._scenario = scenario
        self._iam_scenario = scenario

        self.start_year_fair = _FAIR_START_YEAR
        self.start_year_justice = self._iam_start_year
        self.end_year_fair = self._iam_end_year
        self.end_year_justice = self._iam_end_year
        self.timestep_justice = 1

        self.justice_start_index = self._iam_start_year - _FAIR_START_YEAR

        self._fill_fair_data([scenario], ensemble_size)

        self._purge_emissions([scenario])

        if (self._co2_indices.sum() + self._co2_ffi_indices.sum()
                + self._co2_afolu_indices.sum() == 3):
            self.emissions[..., self._co2_indices] = (
                self.emissions[..., self._co2_ffi_indices].data
                + self.emissions[..., self._co2_afolu_indices].data
            )

        self.cumulative_emissions[1:, ...] = (
            self.emissions.cumsum(dim="timepoints", skipna=False) * self.timestep
            + self.cumulative_emissions[0, ...]
        ).data

        self._cache_arrays()

        if self._routine_flags["ghg"] and self.ghg_method == "meinshausen2020":
            self.ghg_forcing_offset = meinshausen2020(
                self.baseline_concentration_array[None, None, ...],
                self.forcing_reference_concentration_array[None, None, ...],
                self.forcing_scale_array[None, None, ...],
                self.greenhouse_gas_radiative_efficiency_array[None, None, ...],
                self._co2_indices, self._ch4_indices, self._n2o_indices,
                self._minor_ghg_indices,
            )

        self.forcing_sum_array[0:1, ...] = np.nansum(
            self.forcing_array[0:1, ...], axis=SPECIES_AXIS
        )
        self.cummins_state_array[0, ..., 0] = self.forcing_sum_array[0, ...]
        self.cummins_state_array[..., 1:] = self.temperature.data

        for i in range(self.justice_start_index):
            self._stepwise_run(i)

        t_init = self.cummins_state_array[self.justice_start_index, 0, :, 1]
        n = self.ensemble_size
        self.t_at[0, :] = t_init[:n]

        self._ecs_values = None

    def _fill_fair_data(self, scenarios: list, ensemble_size: int):
        self.define_time(_FAIR_START_YEAR, self._iam_end_year + 1, 1)
        self.define_scenarios(scenarios)

        df_configs = pd.read_csv(
            os.path.join(self._data_path, "calibrated_constrained_parameters.csv"),
            index_col=0,
        )

        if ensemble_size < len(df_configs):
            df_configs = df_configs.iloc[:ensemble_size]

        self.define_configs(df_configs.index)
        self.number_of_ensembles = len(df_configs.index)

        species, properties = read_properties(
            filename=os.path.join(
                self._data_path, "species_configs_properties_calibration.csv"
            )
        )
        self.define_species(species, properties)
        self.allocate()

        self._fill_rcmip(scenarios)

        df_emis = pd.read_csv(
            os.path.join(self._data_path, "rcmip_emissions_annual.csv")
        )
        gfed_sectors = [
            "Emissions|NOx|MAGICC AFOLU|Agricultural Waste Burning",
            "Emissions|NOx|MAGICC AFOLU|Forest Burning",
            "Emissions|NOx|MAGICC AFOLU|Grassland Burning",
            "Emissions|NOx|MAGICC AFOLU|Peat Burning",
        ]
        for scenario in scenarios:
            self.emissions.loc[dict(specie="NOx", scenario=scenario)] = (
                df_emis.loc[
                    (df_emis["Scenario"] == scenario) & (df_emis["Region"] == "World")
                    & (df_emis["Variable"].isin(gfed_sectors)),
                    str(_FAIR_START_YEAR):str(self._iam_end_year),
                ].interpolate(axis=1).values.squeeze().sum(axis=0) * 46.006 / 30.006
                + df_emis.loc[
                    (df_emis["Scenario"] == scenario) & (df_emis["Region"] == "World")
                    & (df_emis["Variable"] == "Emissions|NOx|MAGICC AFOLU|Agriculture"),
                    str(_FAIR_START_YEAR):str(self._iam_end_year),
                ].interpolate(axis=1).values.squeeze()
                + df_emis.loc[
                    (df_emis["Scenario"] == scenario) & (df_emis["Region"] == "World")
                    & (df_emis["Variable"] == "Emissions|NOx|MAGICC Fossil and Industrial"),
                    str(_FAIR_START_YEAR):str(self._iam_end_year),
                ].interpolate(axis=1).values.squeeze()
            )[:self.emissions.shape[0], None]

        fill(self.climate_configs["ocean_heat_capacity"],
             df_configs.loc[:, "clim_c1":"clim_c3"].values)
        fill(self.climate_configs["ocean_heat_transfer"],
             df_configs.loc[:, "clim_kappa1":"clim_kappa3"].values)
        fill(self.climate_configs["deep_ocean_efficacy"],
             df_configs["clim_epsilon"].values.squeeze())
        fill(self.climate_configs["gamma_autocorrelation"],
             df_configs["clim_gamma"].values.squeeze())
        fill(self.climate_configs["sigma_eta"],
             df_configs["clim_sigma_eta"].values.squeeze())
        fill(self.climate_configs["sigma_xi"],
             df_configs["clim_sigma_xi"].values.squeeze())
        fill(self.climate_configs["seed"], df_configs["seed"])
        fill(self.climate_configs["stochastic_run"], False)  # deterministic for speed
        fill(self.climate_configs["use_seed"], True)
        fill(self.climate_configs["forcing_4co2"], df_configs["clim_F_4xCO2"])

        self.fill_species_configs(
            filename=os.path.join(
                self._data_path, "species_configs_properties_calibration.csv"
            )
        )

        fill(self.species_configs["iirf_0"],
             df_configs["cc_r0"].values.squeeze(), specie="CO2")
        fill(self.species_configs["iirf_airborne"],
             df_configs["cc_rA"].values.squeeze(), specie="CO2")
        fill(self.species_configs["iirf_uptake"],
             df_configs["cc_rU"].values.squeeze(), specie="CO2")
        fill(self.species_configs["iirf_temperature"],
             df_configs["cc_rT"].values.squeeze(), specie="CO2")

        fill(self.species_configs["aci_scale"],
             df_configs["aci_beta"].values.squeeze())
        fill(self.species_configs["aci_shape"],
             df_configs["aci_shape_so2"].values.squeeze(), specie="Sulfur")
        fill(self.species_configs["aci_shape"],
             df_configs["aci_shape_bc"].values.squeeze(), specie="BC")
        fill(self.species_configs["aci_shape"],
             df_configs["aci_shape_oc"].values.squeeze(), specie="OC")

        for sp in ["BC", "CH4", "N2O", "NH3", "NOx", "OC", "Sulfur", "VOC",
                   "Equivalent effective stratospheric chlorine"]:
            fill(self.species_configs["erfari_radiative_efficiency"],
                 df_configs[f"ari_{sp}"], specie=sp)

        for sp in ["CO2", "CH4", "N2O", "Stratospheric water vapour", "Contrails",
                   "Light absorbing particles on snow and ice", "Land use"]:
            fill(self.species_configs["forcing_scale"],
                 df_configs[f"fscale_{sp}"].values.squeeze(), specie=sp)

        halo_species = [
            "CFC-11", "CFC-12", "CFC-113", "CFC-114", "CFC-115", "HCFC-22",
            "HCFC-141b", "HCFC-142b", "CCl4", "CHCl3", "CH2Cl2", "CH3Cl",
            "CH3CCl3", "CH3Br", "Halon-1211", "Halon-1301", "Halon-2402",
            "CF4", "C2F6", "C3F8", "c-C4F8", "C4F10", "C5F12", "C6F14",
            "C7F16", "C8F18", "NF3", "SF6", "SO2F2", "HFC-125", "HFC-134a",
            "HFC-143a", "HFC-152a", "HFC-227ea", "HFC-23", "HFC-236fa",
            "HFC-245fa", "HFC-32", "HFC-365mfc", "HFC-4310mee",
        ]
        for sp in halo_species:
            fill(self.species_configs["forcing_scale"],
                 df_configs["fscale_minorGHG"].values.squeeze(), specie=sp)

        for sp in ["CH4", "N2O", "Equivalent effective stratospheric chlorine",
                   "CO", "VOC", "NOx"]:
            fill(self.species_configs["ozone_radiative_efficiency"],
                 df_configs[f"o3_{sp}"], specie=sp)

        fill(self.species_configs["baseline_concentration"],
             df_configs["cc_co2_concentration_1750"].values.squeeze(), specie="CO2")

        initialise(self.concentration, self.species_configs["baseline_concentration"])
        initialise(self.forcing, 0)
        initialise(self.temperature, 0)
        initialise(self.cumulative_emissions, 0)
        initialise(self.airborne_emissions, 0)

        self._check_properties()
        self._make_indices()
        if self._routine_flags["temperature"]:
            with warnings.catch_warnings():
                if _SUPPRESS_WARNINGS:
                    warnings.filterwarnings("ignore", category=RuntimeWarning,
                                            module="scipy.stats._multivariate")
                self._make_ebms()

    def _fill_rcmip(self, scenarios: list):
        species_to_rcmip = {sp: sp.replace("-", "") for sp in self.species}
        species_to_rcmip["CO2 FFI"] = "CO2|MAGICC Fossil and Industrial"
        species_to_rcmip["CO2 AFOLU"] = "CO2|MAGICC AFOLU"
        species_to_rcmip["NOx aviation"] = "NOx|MAGICC Fossil and Industrial|Aircraft"
        species_to_rcmip["Aerosol-radiation interactions"] = "Aerosols-radiation interactions"
        species_to_rcmip["Aerosol-cloud interactions"] = "Aerosols-radiation interactions"
        species_to_rcmip["Contrails"] = "Contrails and Contrail-induced Cirrus"
        species_to_rcmip["Light absorbing particles on snow and ice"] = "BC on Snow"
        species_to_rcmip["Stratospheric water vapour"] = "CH4 Oxidation Stratospheric H2O"
        species_to_rcmip["Land use"] = "Albedo Change"

        species_to_rcmip = {k: v for k, v in species_to_rcmip.items()
                            if k in self.species}

        df_emis = pd.read_csv(os.path.join(self._data_path, "rcmip_emissions_annual.csv"))
        df_conc = pd.read_csv(os.path.join(self._data_path, "rcmip_concentrations_annual.csv"))
        df_forc = pd.read_csv(os.path.join(self._data_path, "rcmip_forcing_annual.csv"))

        for scenario in scenarios:
            for specie, rcmip_name in species_to_rcmip.items():
                mode = self.properties_df.loc[specie, "input_mode"]

                if mode == "emissions":
                    rows = df_emis.loc[
                        (df_emis["Scenario"] == scenario)
                        & df_emis["Variable"].str.endswith("|" + rcmip_name)
                        & (df_emis["Region"] == "World"),
                        "1750":"2500",
                    ].interpolate(axis=1).values.squeeze()
                    if rows.shape[0] == 0:
                        continue
                    notnan = np.nonzero(~np.isnan(rows))
                    interp = interp1d(np.arange(1750.5, 2501.5)[notnan], rows[notnan],
                                     fill_value="extrapolate", bounds_error=False)
                    emis = interp(self.timepoints)
                    emis[self.timepoints < 1750] = np.nan
                    emis[self.timepoints > 2501] = np.nan

                    unit = df_emis.loc[
                        (df_emis["Scenario"] == scenario)
                        & df_emis["Variable"].str.endswith("|" + rcmip_name)
                        & (df_emis["Region"] == "World"),
                        "Unit",
                    ].values[0]
                    emis = emis * (
                        prefix_convert[unit.split()[0]][desired_emissions_units[specie].split()[0]]
                        * compound_convert[unit.split()[1].split("/")[0]][
                            desired_emissions_units[specie].split()[1].split("/")[0]]
                        * time_convert[unit.split()[1].split("/")[1]][
                            desired_emissions_units[specie].split()[1].split("/")[1]]
                    )
                    fill(self.emissions, emis[:, None], specie=specie, scenario=scenario)

                elif mode == "concentration":
                    rows = df_conc.loc[
                        (df_conc["Scenario"] == scenario)
                        & df_conc["Variable"].str.endswith("|" + rcmip_name)
                        & (df_conc["Region"] == "World"),
                        "1700":"2500",
                    ].interpolate(axis=1).values.squeeze()
                    if rows.shape[0] == 0:
                        continue
                    notnan = np.nonzero(~np.isnan(rows))
                    interp = interp1d(np.arange(1700.5, 2501.5)[notnan], rows[notnan],
                                     fill_value="extrapolate", bounds_error=False)
                    conc = interp(self.timebounds)
                    conc[self.timebounds < 1700] = np.nan
                    conc[self.timebounds > 2501] = np.nan

                    unit = df_conc.loc[
                        (df_conc["Scenario"] == scenario)
                        & df_conc["Variable"].str.endswith("|" + rcmip_name)
                        & (df_conc["Region"] == "World"),
                        "Unit",
                    ].values[0]
                    conc = conc * mixing_ratio_convert[unit][desired_concentration_units[specie]]
                    fill(self.concentration, conc[:, None], specie=specie, scenario=scenario)

                elif mode == "forcing":
                    rows = df_forc.loc[
                        (df_forc["Scenario"] == scenario)
                        & df_forc["Variable"].str.endswith("|" + rcmip_name)
                        & (df_forc["Region"] == "World"),
                        "1750":"2500",
                    ].interpolate(axis=1).values.squeeze()
                    if rows.shape[0] == 0:
                        continue
                    notnan = np.nonzero(~np.isnan(rows))
                    interp = interp1d(np.arange(1750.5, 2501.5)[notnan], rows[notnan],
                                     fill_value="extrapolate", bounds_error=False)
                    forc = interp(self.timebounds)
                    forc[self.timebounds < 1750] = np.nan
                    forc[self.timebounds > 2501] = np.nan
                    fill(self.forcing, forc[:, None], specie=specie, scenario=scenario)

    def _purge_emissions(self, scenarios: list):
        for scenario in scenarios:
            rcmip_arr = self.emissions.sel(specie="CO2 FFI", scenario=scenario)
            purge = np.full((self._iam_end_year - _FAIR_START_YEAR + 1, 1,
                             self.number_of_ensembles), np.nan)
            purge[:self.justice_start_index] = rcmip_arr[:self.justice_start_index].values[:, None, :]
            fill(self.emissions, purge, specie="CO2 FFI")

    def _cache_arrays(self):
        self.alpha_lifetime_array = self.alpha_lifetime.data
        self.airborne_emissions_array = self.airborne_emissions.data
        self.baseline_concentration_array = self.species_configs["baseline_concentration"].data
        self.baseline_emissions_array = self.species_configs["baseline_emissions"].data
        self.br_atoms_array = self.species_configs["br_atoms"].data
        self.ch4_lifetime_chemical_sensitivity_array = self.species_configs[
            "ch4_lifetime_chemical_sensitivity"].data
        self.lifetime_temperature_sensitivity_array = self.species_configs[
            "lifetime_temperature_sensitivity"].data
        self.cl_atoms_array = self.species_configs["cl_atoms"].data
        self.concentration_array = self.concentration.data
        self.concentration_per_emission_array = self.species_configs[
            "concentration_per_emission"].data
        self.contrails_radiative_efficiency_array = self.species_configs[
            "contrails_radiative_efficiency"].data
        self.cummins_state_array = (
            np.ones((self._n_timebounds, self._n_scenarios, self._n_configs,
                     self._n_layers + 1)) * np.nan
        )
        self.deep_ocean_efficacy_array = self.climate_configs["deep_ocean_efficacy"].data
        self.erfari_radiative_efficiency_array = self.species_configs[
            "erfari_radiative_efficiency"].data
        self.erfaci_scale_array = self.species_configs["aci_scale"].data
        self.erfaci_shape_array = self.species_configs["aci_shape"].data
        self.forcing_array = self.forcing.data
        self.forcing_scale_array = (
            self.species_configs["forcing_scale"].data
            * (1 + self.species_configs["tropospheric_adjustment"].data)
        )
        self.forcing_efficacy_array = self.species_configs["forcing_efficacy"].data
        self.forcing_efficacy_sum_array = (
            np.ones((self._n_timebounds, self._n_scenarios, self._n_configs)) * np.nan
        )
        self.forcing_reference_concentration_array = self.species_configs[
            "forcing_reference_concentration"].data
        self.forcing_sum_array = self.forcing_sum.data
        self.forcing_temperature_feedback_array = self.species_configs[
            "forcing_temperature_feedback"].data
        self.fractional_release_array = self.species_configs["fractional_release"].data
        self.g0_array = self.species_configs["g0"].data
        self.g1_array = self.species_configs["g1"].data
        self.gas_partitions_array = self.gas_partitions.data
        self.greenhouse_gas_radiative_efficiency_array = self.species_configs[
            "greenhouse_gas_radiative_efficiency"].data
        self.h2o_stratospheric_factor_array = self.species_configs[
            "h2o_stratospheric_factor"].data
        self.iirf_0_array = self.species_configs["iirf_0"].data
        self.iirf_airborne_array = self.species_configs["iirf_airborne"].data
        self.iirf_temperature_array = self.species_configs["iirf_temperature"].data
        self.iirf_uptake_array = self.species_configs["iirf_uptake"].data
        self.land_use_cumulative_emissions_to_forcing_array = self.species_configs[
            "land_use_cumulative_emissions_to_forcing"].data
        self.lapsi_radiative_efficiency_array = self.species_configs[
            "lapsi_radiative_efficiency"].data
        self.ocean_heat_transfer_array = self.climate_configs["ocean_heat_transfer"].data
        self.ozone_radiative_efficiency_array = self.species_configs[
            "ozone_radiative_efficiency"].data
        self.partition_fraction_array = self.species_configs["partition_fraction"].data
        self.unperturbed_lifetime_array = self.species_configs["unperturbed_lifetime"].data
        self.cumulative_emissions_array = self.cumulative_emissions.data
        self.emissions_array = self.emissions.data

        if self._routine_flags["temperature"]:
            self.eb_matrix_d_array = self.ebms["eb_matrix_d"].data
            self.forcing_vector_d_array = self.ebms["forcing_vector_d"].data
            self.stochastic_d_array = self.ebms["stochastic_d"].data

        self.co2_idx = int(np.where(self._co2_indices)[0][0])
        self.co2_ffi_idx = int(np.where(self._co2_ffi_indices)[0][0])
        self.co2_afolu_idx = int(np.where(self._co2_afolu_indices)[0][0])

    def _stepwise_run(self, i: int):
        if self._routine_flags["ghg"]:
            self.alpha_lifetime_array[i:i+1, ..., self._ghg_indices] = calculate_alpha(
                self.airborne_emissions_array[i:i+1, ..., self._ghg_indices],
                self.cumulative_emissions_array[i:i+1, ..., self._ghg_indices],
                self.g0_array[None, None, ..., self._ghg_indices],
                self.g1_array[None, None, ..., self._ghg_indices],
                self.iirf_0_array[None, None, ..., self._ghg_indices],
                self.iirf_airborne_array[None, None, ..., self._ghg_indices],
                self.iirf_temperature_array[None, None, ..., self._ghg_indices],
                self.iirf_uptake_array[None, None, ..., self._ghg_indices],
                self.cummins_state_array[i:i+1, ..., 1:2],
                self.iirf_max,
            )

        if self.ch4_method == "thornhill2021":
            self.alpha_lifetime_array[i:i+1, ..., self._ch4_indices] = calculate_alpha_ch4(
                self.emissions_array[i:i+1, ...],
                self.concentration_array[i:i+1, ...],
                self.cummins_state_array[i:i+1, ..., 1:2],
                self.baseline_emissions_array[None, None, ...],
                self.baseline_concentration_array[None, None, ...],
                self.ch4_lifetime_chemical_sensitivity_array[None, None, ...],
                self.lifetime_temperature_sensitivity_array[None, None, :, None],
                self._aerosol_chemistry_from_emissions_indices,
                self._aerosol_chemistry_from_concentration_indices,
            )

        (
            self.concentration_array[i+1:i+2, ..., self._ghg_forward_indices],
            self.gas_partitions_array[..., self._ghg_forward_indices, :],
            self.airborne_emissions_array[i+1:i+2, ..., self._ghg_forward_indices],
        ) = step_concentration(
            self.emissions_array[i:i+1, ..., self._ghg_forward_indices, None],
            self.gas_partitions_array[..., self._ghg_forward_indices, :],
            self.airborne_emissions_array[i+1:i+2, ..., self._ghg_forward_indices, None],
            self.alpha_lifetime_array[i:i+1, ..., self._ghg_forward_indices, None],
            self.baseline_concentration_array[None, None, ..., self._ghg_forward_indices],
            self.baseline_emissions_array[None, None, ..., self._ghg_forward_indices, None],
            self.concentration_per_emission_array[None, None, ..., self._ghg_forward_indices],
            self.unperturbed_lifetime_array[None, None, ..., self._ghg_forward_indices, :],
            self.partition_fraction_array[None, None, ..., self._ghg_forward_indices, :],
            self.timestep,
        )

        (
            self.emissions_array[i:i+1, ..., self._ghg_inverse_indices],
            self.gas_partitions_array[..., self._ghg_inverse_indices, :],
            self.airborne_emissions_array[i+1:i+2, ..., self._ghg_inverse_indices],
        ) = unstep_concentration(
            self.concentration_array[i+1:i+2, ..., self._ghg_inverse_indices],
            self.gas_partitions_array[None, ..., self._ghg_inverse_indices, :],
            self.airborne_emissions_array[i:i+1, ..., self._ghg_inverse_indices, None],
            self.alpha_lifetime_array[i:i+1, ..., self._ghg_inverse_indices, None],
            self.baseline_concentration_array[None, None, ..., self._ghg_inverse_indices],
            self.baseline_emissions_array[None, None, ..., self._ghg_inverse_indices],
            self.concentration_per_emission_array[None, None, ..., self._ghg_inverse_indices],
            self.unperturbed_lifetime_array[None, None, ..., self._ghg_inverse_indices, :],
            self.partition_fraction_array[None, None, ..., self._ghg_inverse_indices, :],
            self.timestep,
        )
        self.cumulative_emissions_array[i+1, ..., self._ghg_inverse_indices] = (
            self.cumulative_emissions_array[i, ..., self._ghg_inverse_indices]
            + self.emissions_array[i, ..., self._ghg_inverse_indices] * self.timestep
        )

        if self.ghg_method == "meinshausen2020":
            self.forcing_array[i+1:i+2, ..., self._ghg_indices] = (
                meinshausen2020(
                    self.concentration_array[i+1:i+2, ...],
                    self.forcing_reference_concentration_array[None, None, ...]
                    * np.ones((1, self._n_scenarios, self._n_configs, self._n_species)),
                    self.forcing_scale_array[None, None, ...],
                    self.greenhouse_gas_radiative_efficiency_array[None, None, ...],
                    self._co2_indices, self._ch4_indices, self._n2o_indices,
                    self._minor_ghg_indices,
                )[0:1, ..., self._ghg_indices]
                - self.ghg_forcing_offset[..., self._ghg_indices]
            )

        if self._routine_flags["ari"]:
            self.forcing_array[i+1:i+2, ..., self._ari_indices] = calculate_erfari_forcing(
                self.emissions_array[i:i+1, ...],
                self.concentration_array[i+1:i+2, ...],
                self.baseline_emissions_array[None, None, ...],
                self.baseline_concentration_array[None, None, ...],
                self.forcing_scale_array[None, None, ..., self._ari_indices],
                self.erfari_radiative_efficiency_array[None, None, ...],
                self._aerosol_chemistry_from_emissions_indices,
                self._aerosol_chemistry_from_concentration_indices,
            )

        if self._routine_flags["aci"]:
            self.forcing_array[i+1:i+2, ..., self._aci_indices] = logsum(
                self.emissions_array[i:i+1, ...],
                self.concentration_array[i+1:i+2, ...],
                self.baseline_emissions_array[None, None, ...],
                self.baseline_concentration_array[None, None, ...],
                self.forcing_scale_array[None, None, ..., self._aci_indices],
                self.erfaci_scale_array[None, None, :],
                self.erfaci_shape_array[None, None, ...],
                self._aerosol_chemistry_from_emissions_indices,
                self._aerosol_chemistry_from_concentration_indices,
            )

        if self._routine_flags["eesc"]:
            self.concentration_array[i+1:i+2, ..., self._eesc_indices] = calculate_eesc(
                self.concentration_array[i+1:i+2, ...],
                self.fractional_release_array[None, None, ...],
                self.cl_atoms_array[None, None, ...],
                self.br_atoms_array[None, None, ...],
                self._cfc11_indices, self._halogen_indices, self.br_cl_ods_potential,
            )

        if self._routine_flags["ozone"]:
            self.forcing_array[i+1:i+2, ..., self._ozone_indices] = thornhill2021(
                self.emissions_array[i:i+1, ...],
                self.concentration_array[i+1:i+2, ...],
                self.baseline_emissions_array[None, None, ...],
                self.baseline_concentration_array[None, None, ...],
                self.forcing_scale_array[None, None, ..., self._ozone_indices],
                self.ozone_radiative_efficiency_array[None, None, ...],
                self._aerosol_chemistry_from_emissions_indices,
                self._aerosol_chemistry_from_concentration_indices,
            )

        if self._routine_flags["contrails"]:
            self.forcing_array[i+1:i+2, ..., self._contrails_indices] = calculate_linear_forcing(
                self.emissions_array[i:i+1, ...], 0,
                self.forcing_scale_array[None, None, ..., self._contrails_indices],
                self.contrails_radiative_efficiency_array[None, None, ...],
            )

        if self._routine_flags["lapsi"]:
            self.forcing_array[i+1:i+2, ..., self._lapsi_indices] = calculate_linear_forcing(
                self.emissions_array[i:i+1, ...],
                self.baseline_emissions_array[None, None, ...],
                self.forcing_scale_array[None, None, ..., self._lapsi_indices],
                self.lapsi_radiative_efficiency_array[None, None, ...],
            )

        if self._routine_flags["h2o stratospheric"]:
            self.forcing_array[i+1:i+2, ..., self._h2ostrat_indices] = calculate_linear_forcing(
                self.forcing_array[i+1:i+2, ...], 0,
                self.forcing_scale_array[None, None, ..., self._h2ostrat_indices],
                self.h2o_stratospheric_factor_array[None, None, ...],
            )

        if self._routine_flags["land use"]:
            self.forcing_array[i+1:i+2, ..., self._landuse_indices] = calculate_linear_forcing(
                self.cumulative_emissions_array[i+1:i+2, ...], 0,
                self.forcing_scale_array[None, None, ..., self._landuse_indices],
                self.land_use_cumulative_emissions_to_forcing_array[None, None, ...],
            )

        self.forcing_array[i+1:i+2, ...] = (
            self.forcing_array[i+1:i+2, ...]
            + self.cummins_state_array[i:i+1, ..., 1:2]
            * self.forcing_temperature_feedback_array[None, None, ...]
        )

        self.forcing_sum_array[i+1:i+2, ...] = np.nansum(
            self.forcing_array[i+1:i+2, ...], axis=SPECIES_AXIS
        )
        self.forcing_efficacy_sum_array[i+1:i+2, ...] = np.nansum(
            self.forcing_array[i+1:i+2, ...] * self.forcing_efficacy_array[None, None, ...],
            axis=SPECIES_AXIS,
        )

        if self._routine_flags["temperature"]:
            self.cummins_state_array[i+1:i+2, ...] = step_temperature(
                self.cummins_state_array[i:i+1, ...],
                self.eb_matrix_d_array[None, None, ...],
                self.forcing_vector_d_array[None, None, ...],
                self.stochastic_d_array[i+1:i+2, None, ...],
                self.forcing_efficacy_sum_array[i+1:i+2, ..., None],
            )

    def step(self, ti: int, global_emiss_gtco2: float, elapsed: float) -> tuple:
        fair_t = ti + self.justice_start_index

        emiss_gt = global_emiss_gtco2
        self.emissions_array[fair_t, 0, :, self.co2_ffi_idx] = emiss_gt
        self.emissions_array[fair_t, 0, :, self.co2_idx] = (
            self.emissions_array[fair_t, 0, :, self.co2_ffi_idx]
            + self.emissions_array[fair_t, 0, :, self.co2_afolu_idx]
        )
        self.cumulative_emissions_array[fair_t+1, 0, :, self.co2_ffi_idx] = (
            self.cumulative_emissions_array[fair_t, 0, :, self.co2_ffi_idx] + emiss_gt
        )
        self.cumulative_emissions_array[fair_t+1, 0, :, self.co2_idx] = (
            self.cumulative_emissions_array[fair_t+1, 0, :, self.co2_ffi_idx]
            + self.cumulative_emissions_array[fair_t+1, 0, :, self.co2_afolu_idx]
        )

        self._stepwise_run(fair_t)

        n = self.ensemble_size
        temp = self.cummins_state_array[fair_t+1, 0, :n, 1]  # surface layer
        self.t_at[ti, :] = temp
        mean_temp = float(temp.mean())

        total_forcing = float(self.forcing_sum_array[fair_t+1, 0, :n].mean())
        self.forcing[ti] = total_forcing

        self.f_co2[ti] = float(
            self.forcing_array[fair_t+1, 0, :n, self.co2_idx].mean()
        )
        self.f_ex[ti] = total_forcing - self.f_co2[ti]

        co2_ppm = float(
            self.concentration_array[fair_t+1, 0, :n, self.co2_idx].mean()
        )
        self._co2_ppm_out[ti] = co2_ppm
        self._m_at_out[ti] = co2_ppm * 2.13  # ppm → GtC

        return mean_temp, total_forcing

    @property
    def t_at_mean(self) -> np.ndarray:
        return self.t_at.mean(axis=1)

    @property
    def t_at_median(self) -> np.ndarray:
        return np.median(self.t_at, axis=1)

    def percentile(self, p: float) -> np.ndarray:
        return np.percentile(self.t_at, p, axis=1)

    @property
    def ecs_values(self) -> np.ndarray:
        if self._ecs_values is None:
            # F_4xCO2 / (4 * lambda), but approximate via config
            self._ecs_values = np.array([3.0] * self.ensemble_size)
        return self._ecs_values

    @property
    def m_at(self) -> np.ndarray:
        return self._m_at_out

    @property
    def co2_ppm(self) -> np.ndarray:
        return self._co2_ppm_out


def download_fair_data(dest_dir: str = None):
    try:
        import pooch
    except ImportError:
        raise ImportError("Install pooch first: pip install pooch")

    here = os.path.dirname(os.path.abspath(__file__))
    if dest_dir is None:
        dest_dir = os.path.normpath(os.path.join(here, "..", "..", "data", "fair_input"))

    os.makedirs(dest_dir, exist_ok=True)

    files = [
        {
            "url": "https://zenodo.org/record/8399112/files/calibrated_constrained_parameters.csv",
            "name": "calibrated_constrained_parameters.csv",
            "hash": "md5:de3b83432b9d071efdd1427ad31e9076",
        },
        {
            "url": "https://raw.githubusercontent.com/OMS-NetZero/FAIR/03aac4fba28bb3c9bf8cf10898df7b7fbeea1359/examples/data/species_configs_properties_calibration1.2.0.csv",
            "name": "species_configs_properties_calibration.csv",
            "hash": "md5:92ed36d299e9b48c7a16acc8fd0f973a",
        },
        {
            "url": "https://zenodo.org/records/4589756/files/rcmip-emissions-annual-means-v5-1-0.csv",
            "name": "rcmip_emissions_annual.csv",
            "hash": "md5:4044106f55ca65b094670e7577eaf9b3",
        },
        {
            "url": "https://zenodo.org/records/4589756/files/rcmip-concentrations-annual-means-v5-1-0.csv",
            "name": "rcmip_concentrations_annual.csv",
            "hash": "md5:0d82c3c3cdd4dd632b2bb9449a5c315f",
        },
        {
            "url": "https://zenodo.org/records/4589756/files/rcmip-radiative-forcing-annual-means-v5-1-0.csv",
            "name": "rcmip_forcing_annual.csv",
            "hash": "md5:87ef6cd4e12ae0b331f516ea7f82ccba",
        },
    ]

    for f in files:
        print(f"Downloading {f['name']} …")
        pooch.retrieve(url=f["url"], path=dest_dir, fname=f["name"], known_hash=f["hash"])
        print(f"  → saved to {os.path.join(dest_dir, f['name'])}")

    print("Done. FAIR data files ready.")


if __name__ == "__main__":
    if "--download" in sys.argv:
        download_fair_data()
    else:
        print("Usage: python -m backend.modules.climate.fair_climate --download")
