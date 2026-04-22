BG = "#0f1623"
SIDEBAR = "#121929"
ACCENT  = "#2a9d8f"
PLOT_BG = "#111827"

REGION_COLORS = [
    "#2a9d8f", "#e9c46a", "#e76f51", "#a8d8ea", "#90be6d",
    "#f4a261", "#c77dff", "#4cc9f0", "#fb8500", "#8338ec", "#06d6a0", "#ff6b6b",
]

TAB_STYLE = {
    "background": "#0a1020", "color": "#4a6a88",
    "border": "none", "borderBottom": "1px solid #1e2d42",
    "padding": "9px 18px", "fontSize": "13px",
}
TAB_SEL = {**TAB_STYLE, "color": ACCENT,
           "borderTop": f"2px solid {ACCENT}", "background": "#161d2e"}

INPUT_STYLE = {
    "background": "#0a1220", "border": "1px solid #243448",
    "color": "#b0c8e0", "borderRadius": "4px",
    "padding": "3px 6px", "fontSize": "12px",
    "outline": "none", "textAlign": "center",
}

DAMAGE_INFO = {
    "quadratic": "Standard DICE (small losses at low temps, accelerates above 2–3°C)",
    "linear": "Proportional to temperature rise (can underestimate high risks near end period)",
    "threshold": "Modest damage below 3 °C, extreme jump above",
}

WELFARE_INFO = {
    "utilitarian": "Ramsey–Koopmans: Uniform damage fraction across all regions (Standard DICE/RICE baseline)",
    "egalitarian": "Amplified damage for poorer regions, higher global effective damage and SCC",
    "rawlsian": "Only considers worst-off region, all regions receive highest regional damage fraction and significantly lowers global GDP",
}
ECONOMY_INFO = {
    "market":  "Fixed savings and capital accumulation rate per region",
    "optimal": "Savings rate converges from market rates toward optimum (high-savers decline and low-savers invest earlier), equalizes regional capital returns",
}

ABOUT_TEXT = [
    ("Integrated Assessment Models (IAMs)", "[insert text]"),
    ("SSP Scenarios", "[insert text]"),
    ("Emission Control Rate μ", "[insert text]"),
    ("Damage Functions", "[insert text]"),
    ("Climate Ensemble", "[insert text]"),
    ("Social Cost of Carbon", "[insert text]"),
]
