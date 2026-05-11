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
        "Simple 2-box energy balance, atmosphere–ocean model calibrated to IPCC AR6 equilibrium climate sensitivity (ECS) distribution."
    ),
    "fair": (
        "More robust multi-gas model, considers CO₂, CH₄, N₂O, aerosols, and carbon-cycle feedbacks separately. Used for constrained warming projections."
    ),
}

ECONOMY_INFO = {
    "market": (
        "Capital accumulation and savings rates are fixed per region. Reflects historical market outcomes with existing market incentives."
    ),
    "optimal": (
        "Global optimizer for maximum welfare. Savings rates converge toward Ramsey-optimum, equalizing marginal returns on capital across regions. High-saving regions reduce rate and low-saving regions invest more."
    ),
}

ABOUT_TEXT = [
    (
        "What is an Integrated Assessment Model (IAM)?",
        """Integrated Assessment Models (IAMs) combine scientific and economic knowledge
to analyze the interactions between climate change and the global economy. They are
the primary tool used by policymakers, the IPCC, and regulatory agencies to evaluate
climate policy.

The **DICE model** (Dynamic Integrated model of Climate and the Economy), developed
by Nobel Laureate William Nordhaus at Yale, is one of the most widely used IAMs in
the world. DICE treats the world as a single economic agent choosing how much to
invest in emissions abatement versus consumption — trading off near-term economic
costs against long-run climate damages.

This dashboard implements a simplified RICE-style version (Regional Integrated model
of Climate and the Economy) with geographic disaggregation into 12 world regions.
The model solves a 5-year time-step optimization from 2015 to 2100, projecting
emissions, temperature, GDP, and climate damages under different policy and model
assumptions. Results are intended for educational exploration and illustrate the
qualitative tradeoffs that real IAMs reveal."""
    ),
    (
        "How IAM Results Shape Climate Policy",
        """IAM outputs directly influence real-world decisions at the highest levels of
government. The U.S. Interagency Working Group relied on DICE and related models
to establish the **Social Cost of Carbon** used in federal regulatory cost-benefit
analysis for over a decade. The IPCC uses IAM scenario ensembles (including SSP
pathways) to frame its Assessment Reports, which in turn inform the Paris Agreement
and national climate commitments.

Policymakers use IAM results to:
- Quantify the economic damage of inaction versus the cost of aggressive mitigation
- Set carbon price trajectories that are cost-effective relative to temperature targets
- Compare the welfare implications of different equity and discount rate assumptions
- Stress-test climate strategies against uncertainty in climate sensitivity and economic growth

IAMs are not crystal balls — they are structured frameworks for reasoning about
complex systems. Their value lies in revealing tradeoffs, not predicting exact futures."""
    ),
    (
        "SSP Scenarios",
        """**Shared Socioeconomic Pathways (SSPs)** are standardized global development
scenarios developed by the IPCC research community to describe plausible futures of
population, economic growth, land use, energy systems, and baseline emissions.

- **SSP1** ("Sustainability"): Low population growth, rapid green transition, strong
  global cooperation. Low baseline emissions.
- **SSP2** ("Middle of the Road"): Continuation of historical trends in development and
  energy. The default DICE calibration scenario.
- **SSP3** ("Regional Rivalry"): Fragmented world with high inequality, slow technology
  diffusion, and high baseline emissions.
- **SSP5** ("Fossil-fueled Development"): High economic growth powered by fossil fuels.
  Highest baseline emissions — hardest to control.

The SSP choice sets the **baseline emissions trajectory before any policy intervention**
— it determines how steeply emissions grow absent climate policy, and thus how
difficult and costly it is to achieve a given temperature target. Policymakers use SSP
scenarios to stress-test climate strategies against uncertainty about future development."""
    ),
    (
        "Emission Control Rate μ and Carbon Policy",
        """The **emission control rate μ (mu)** represents the fraction of industrial CO₂
emissions abated by policy in each period, ranging from 0 (no control) to 1 (full
abatement). In DICE, μ maps to an implicit carbon price through the **marginal
abatement cost (MAC) function** — a higher μ requires a higher carbon price to
achieve.

The DICE 2023 baseline assumes a starting carbon price of ~$6/tCO₂ growing at
2.5%/year, reflecting current global policy reality. The Paris Agreement scenario
projects control rates rising roughly 0.5 percentage points per year after 2030.

**How μ interacts with the rest of the model:**
- Higher μ → lower CO₂ emissions → lower temperature → lower climate damages
- Higher μ → higher abatement costs → lower near-term GDP
- The optimal μ is where the marginal cost of abatement equals the Social Cost of Carbon

Real-world policy instruments that correspond to μ include carbon taxes, cap-and-trade
systems, fuel efficiency standards, and renewable energy mandates. Choosing μ_start
and μ_end lets you explore the cost-benefit tradeoffs of different climate ambition levels
and how quickly a transition must occur to stay within temperature targets."""
    ),
    (
        "Damage Functions",
        """**Damage functions** translate global mean temperature increase into economic
losses expressed as a fraction of GDP. This relationship is one of the most uncertain
and consequential components of any IAM.

The **DICE standard quadratic function** estimates ~2.1% GDP loss at 3°C warming —
calibrated from meta-analyses of sectoral impact studies. Critics argue this
systematically underestimates true damages by omitting non-market impacts (health,
biodiversity, conflict, forced migration) and tail risks (tipping points).

**Why the damage function matters so much:**
Howard and Sterner (2017) showed that using a damage calibration 3× larger than
DICE standard raises the optimal carbon price by a factor of ~3, fundamentally
changing the economics of climate action. The IPCC Sixth Assessment Report warns
that aggregate damage estimates likely understate the full costs of warming.

The **Kalkuhl function** captures an important real-world effect: the *rate* of warming
matters, not just the level. Societies can adapt to gradual change; rapid warming
overwhelms infrastructure, agriculture, and health systems. This rewards smooth
decarbonization pathways and penalizes delayed action followed by rapid catch-up.

**Tipping points** (threshold function) represent discontinuous risks — where a small
additional increment of warming triggers a large, potentially irreversible change.
West Antarctic ice sheet collapse, Amazon dieback, and AMOC disruption are examples
that could make the effective damage function far steeper than any smooth curve."""
    ),
    (
        "Social Cost of Carbon (SCC)",
        """The **Social Cost of Carbon (SCC)** is the present value of all future damages
caused by emitting one additional tonne of CO₂ today. It is the key metric linking
climate science to economic policy.

The SCC represents the **external cost** of carbon emissions not captured by market
prices. If firms and consumers paid the SCC for each tonne of CO₂, they would
internalize the full social cost of their decisions — the economic rationale for a
carbon tax or cap-and-trade system.

**DICE 2023 estimates:** approximately $60–200/tCO₂ depending on the discount
rate and damage function — up significantly from earlier versions due to updated
damage estimates and lower interest rates.

**The discount rate controversy:** The SCC is hypersensitive to the discount rate.
A 1% discount rate (Stern Review, 2006) values far-future damages almost as
highly as current ones, yielding an SCC ~10× higher than Nordhaus's ~5% rate.
This is not a technical disagreement — it is fundamentally a question of how much
we value the welfare of future generations relative to our own.

The SCC is used in U.S. regulatory impact assessments to justify emissions
regulations, in court challenges to fossil fuel projects, and in corporate climate
risk disclosures. Getting it right is therefore not merely academic."""
    ),
    (
        "Climate Ensemble and Uncertainty",
        """**Equilibrium Climate Sensitivity (ECS)** — the warming that results from a
sustained doubling of atmospheric CO₂ — is the dominant source of climate
projection uncertainty. The IPCC AR6 estimates ECS at 2.5–4.0°C (likely range),
with a best estimate of ~3°C.

This model runs **multiple ensemble members** by drawing ECS values from a
distribution consistent with AR6. The resulting spread of temperature outcomes
(shown as the 5–95% range in the Temperature tab) represents the plausible
warming envelope under a given emissions pathway.

**Why the ensemble matters for policy:**
Even if the best-estimate warming from a given policy scenario is acceptable,
the upper tail of the distribution may not be. A 5% chance of 5°C warming
represents a genuine catastrophic risk — the case for **precautionary policy**
even when median outcomes seem manageable.

The **DICE 2-box model** is a simple energy balance model calibrated to match the
AR6 ECS distribution. The **FaIR v2** option is a more sophisticated impulse
response model capturing gas-by-gas forcing, carbon-cycle feedbacks, and ocean
heat uptake — closer to what the IPCC uses for constrained projections."""
    ),
    (
        "Welfare Functions and Climate Justice",
        """Standard DICE uses a **utilitarian welfare function**: it maximizes the global
sum of discounted population-weighted utilities, treating all consumers equally at
the margin. A dollar of climate damage to a low-income country counts the same
as a dollar of damage to a wealthy one. This is the mainstream economic approach
but is increasingly challenged on equity grounds.

**Climate justice dimensions of welfare choice:**
Developing regions are often the most vulnerable to climate damages — through
extreme heat, sea-level rise, agricultural disruption, and health impacts — yet
have contributed the least to cumulative CO₂ emissions. The utilitarian framework
can systematically undervalue their losses if their economic output is small.

Alternative welfare functions directly address this:

- **Prioritarian**: Worse-off regions count more — leads to higher optimal carbon
  prices and more aggressive abatement
- **Sufficientarian**: Guarantees a minimum consumption floor before aggregate
  optimization — relevant for linking climate policy to development goals
- **Egalitarian**: Penalizes inequality — discourages policies that improve average
  outcomes while widening regional gaps

The welfare function choice changes not just the SCC, but who is deemed responsible
for reducing emissions and who should receive climate finance — questions at the
center of UNFCCC negotiations."""
    ),
    (
        "How to Read the Results",
        """The graphs in this model are designed to reveal how economic decisions interact
with physical outcomes and welfare consequences. Key relationships to explore:

**Emissions ↔ Temperature:** Higher μ reduces CO₂ and slows warming, but
temperature responds with a lag — early action prevents lock-in of long-run warming
that later action cannot undo.

**Abatement cost ↔ GDP:** The MAC (Marginal Abatement Cost) shows the economic
cost of each additional unit of control. If the MAC is below the SCC, more abatement
is welfare-improving; if above, it is not yet cost-effective.

**Regional equity:** The Welfare & Damages tab shows that climate change is deeply
unequal — tropical and lower-income regions typically face disproportionate damage
relative to their economic share. The welfare function choice changes which regions'
burdens are prioritized.

**Uncertainty:** The temperature ensemble communicates the range of outcomes
that are physically plausible — not just the best estimate. A policy that looks
adequate at the median may still carry significant tail risk.

**IAM results do not prescribe policy** — they illuminate tradeoffs. The most
important output is not any single number but the *relationships* between choices
and outcomes across scenarios, and how sensitive results are to key assumptions
about damages, discount rates, and development pathways."""
    ),
]
