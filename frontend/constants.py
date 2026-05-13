BG = "#0f1623"
SIDEBAR = "#121929"
ACCENT  = "#2a9d8f"
PLOT_BG = "#111827"

REGION_COLORS = [
    "#2a9d8f", "#e9c46a", "#e76f51", "#a8d8ea", "#90be6d",
    "#f4a261", "#c77dff", "#4cc9f0", "#fb8500", "#8338ec", "#06d6a0", "#ff6b6b",
]

TAB_STYLE = {
    "background": "#0a1020", "color": "#9fbcce",
    "border": "none", "borderBottom": "1px solid #1e2d42",
    "padding": "9px 18px", "fontSize": "14px",
}
TAB_SEL = {**TAB_STYLE, "color": ACCENT,
           "borderTop": f"2px solid {ACCENT}", "background": "#161d2e"}

INPUT_STYLE = {
    "background": "#0a1220", "border": "1px solid #243448",
    "color": "#b0c8e0", "borderRadius": "0",
    "padding": "3px 6px", "fontSize": "13px",
    "outline": "none", "textAlign": "center",
}

SSP_INFO = {
    "SSP1": (
        "Lowest warming trajectory. Low challenges to mitigation and adaptation. Prioritizes human well-being and clean energy with low material growth and resource intensity."
    ),
    "SSP2": (
        "Middle-ground warming outcome. Moderate challenges to mitigation and adaptation. Follows historical trends in emissions without major policy change."
    ),
    "SSP3": (
        "Higher warming outcome. High challenges to mitigation and adaptation. Heavy reliance on fossil fuels. Focus placed on regional issues rather than global."
    ),
    "SSP4": (
        "Moderate warming. High adaptation challenges and few mitigation challenges. High vulnerability and extremely unequal economic growth in poorer regions."
    ),
    "SSP5": (
        "Highest warming projection. High mitigation challenges and few adaptation challenges. Rapid economic growth powered by fossil fuels."
    ),
}

DAMAGE_INFO = {
    "quadratic": (
        "Standard DICE/RICE, accelerates non-linearly at high temperatures but underestimates tail risks, tipping points, and non-market damage."
    ),
    "linear": (
        "Damage proportional to temperature, underestimates high-end rise. Used for determining lower bound when comparing scenarios but not for policy optimization."
    ),
    "threshold": (
        "Quadratic below 3°C with sharp penalty modeling a climate tipping point such as ice sheet collapse or permafrost feedback."
    ),
    "kalkuhl": (
        "Damage depends on rate of temperature change. Rapid warming causes additional economic disruption. Prefers gradual decarbonization over abrupt policy change."
    ),
}

WELFARE_INFO = {
    "utilitarian": (
        "Standard DICE/RICE, considers regions equally regardless of wealth or vulnerability. Lower carbon prices and less mitigation compared to alternatives that prioritize equity."
    ),
    "prioritarian": (
        "Additional welfare weight to poorer regions. Damages to vulnerable populations weigh more in welfare sum, resulting in higher carbon prices."
    ),
    "sufficientarian": (
        "Prioritizes regions below World Bank poverty line and ensures basic needs are met before before aggregating welfare (development-climate tradeoffs)."
    ),
    "egalitarian": (
        "Equal welfare weight for all generations, considers long-run climate damages and equitable sharing of abatement costs across regions."
    ),
}

CLIMATE_INFO = {
    "dice": (
        "Simple 2-box energy balance, atmosphere–ocean model calibrated to IPCC AR6 ECS distribution."
    ),
    "fair": (
        "More robust multi-gas model, considers CO₂, CH₄, N₂O, aerosols, and carbon-cycle feedbacks separately."
    ),
}

ECONOMY_INFO = {
    "market": (
        "Capital accumulation and savings rates are fixed per region. Reflects historical market outcomes with existing market incentives."
    ),
    "optimal": (
        "Global optimizer for maximum welfare. Savings rates converge toward Ramsey-optimum, equalizing marginal returns on capital across regions."
    ),
}

ABOUT_TEXT = [
(
        "Author",
        """Michelle Liang, ChE418 Spring 2026"""
    ),
    (
        "What is an Integrated Assessment Model (IAM)?",
        """IAMs are tools for predicting emissions growth and temperature rise given a set of restrictions or projections. They are used by policymakers and the IPCC to evaluate mitigation and carbon removal strategies [1].

**DICE** (Dynamic Integrated Model of Climate and the Economy) is a globally aggregated model simplifying economics, politics, and factors like emissions and population [2]. **RICE** (Regional Integrated Model of Climate and the Economy) operates similarly but across 12 regions (Africa, China, EU, Eurasia, India, Japan, Latin America, Middle East, Russia, US) [3].

This website implements a simplified DICE/RICE model with a 5-year time-step from 2025 to 2100."""
    ),
    (
        "SSP Scenarios",
        """**Shared Socioeconomic Pathways (SSPs)** are standardized global development scenarios describing possible futures for population, economic growth, land use, energy systems, and emissions [4].

The SSP sets the baseline emissions trajectory before any policy intervention, specifically how much emissions grow and how costly it is to achieve a given temperature target. Policymakers use SSPs to stress-test climate strategies against uncertainty in future development."""
    ),
    (
        "Emission Control Rate μ and Carbon Policy",
        """The **emission control rate μ** represents the fraction of industrial CO₂ emissions abated by policy, from 0 (no control) to 1 (full abatement). The optimal μ is where the marginal abatement cost (MAC) equals the Social Cost of Carbon (SCC).

- Higher μ → lower CO₂ emissions → lower temperature → lower climate damages
- Higher μ → higher MAC → lower short-term GDP

μ encompasses real-world instruments like carbon taxes, fuel efficiency standards, and renewable energy mandates. Changing μ lets users explore cost-benefit tradeoffs of climate ambition and how quickly policy change must occur to stay within temperature targets."""
    ),
    (
        "Damage Functions",
        """Damage functions translate global mean temperature increase into economic
losses from climate change expressed as a fraction of GDP. Damage functions are the most uncertain and policy-relevant component of IAMs, 
significantly affecting the optimal carbon price and the recommended level of abatement."""
    ),
    (
        "Climate Model",
        """The climate model translates CO₂ emissions into temperature outcomes. Since the relationship between emissions and warming is uncertain, the model runs multiple ensemble members, with slightly different climate sensitivities to produce a range of possible outcomes rather than a single projection."""
    ),
    (
        "Welfare Functions and Climate Justice",
        """The welfare function determines how damages across regions factor into policy evaluation. Developing regions are typically most vulnerable to climate impacts yet have contributed least to cumulative emissions. The welfare choice affects the carbon price and which regions bear the cost of action, which is important to international climate finance negotiations."""
    ),
    (
        "How to Read Results",
        """The graphs show how economic decisions, policy, and physical outcomes affect each other:

- **Emissions <-> Temperature:** Higher μ reduces CO₂ and slows warming. Early action prevents long-term warming that later emissions control cannot undo.
- **MAC <-> GDP:** If the MAC is below the SCC, more abatement is welfare-improving. If above, it is not cost-effective.
- **Regional Equity:** Climate change is unequal as lower-income regions typically face disproportionate damage. The welfare function affects which regions' burdens are prioritized.
- **Uncertainty:** The climate ensemble shows a range of physically plausible outcomes, important for assessing tail risks.

The significance behind IAM results are the tradeoffs between outcomes across scenarios, and how sensitive results are to assumptions about damages, policy, and development pathways, helping users understand how results can drive effective, ethical, and feasible policy."""
    ),
(
        "Citations",
        """
        1. Whittaker, H., Egna, N. & O’Connor-Morberg, S. The role of Integrated Assessment Models in Carbon Removal Policy. Carbon Direct Available at: https://www.carbon-direct.com/insights/the-role-of-integrated-assessment-models-in-carbon-removal-policy.\n
        2. Nordhaus, W. & Sztorc, P. DICE 2023: Introduction and User’s Manual Third Edition (2024). Available at: https://yale.app.box.com/s/whlqcr7gtzdm4nxnrfhvap2hlzebuvvm/file/1539632845931.\n
        3. Kim, D., Park, W. & Jin, T. Evaluating global carbon neutrality commitments: An integrated assessment model approach to the 2°C target. Environmental Science & Policy 174, 104280 (2025).\n
        4. Understanding shared socio-economic pathways (ssps). Understanding Shared Socio-economic Pathways (SSPs) – ClimateData.ca Available at: https://climatedata.ca/resource/understanding-shared-socio-economic-pathways-ssps/. 
"""
    ),
(
        "Acknowledgements",
        """
        I would like to acknowledge Professor Simson for her guidance and support throughout this project.
"""
    ),
]
