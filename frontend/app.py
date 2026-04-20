"""
IAM Frontend — Dash web interface.
Run:  python frontend/app.py   (default port 8050)
Requires the backend to be running:  python backend/api.py

Environment variables
---------------------
IAM_BACKEND_URL   Base URL of the backend (default: http://localhost:5001)
IAM_FRONTEND_PORT Port for this Dash app   (default: 8050)
"""

import os
import json
import urllib.request
import urllib.error

import dash
from dash import dcc, html, Input, Output, State, callback
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── backend connection ─────────────────────────────────────────────────────────

BACKEND_URL = os.environ.get("IAM_BACKEND_URL", "http://localhost:5001")


def _api_get(path: str) -> dict:
    with urllib.request.urlopen(f"{BACKEND_URL}{path}", timeout=10) as resp:
        return json.loads(resp.read())


def _api_post(path: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req  = urllib.request.Request(
        f"{BACKEND_URL}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


# ── load static config from backend ───────────────────────────────────────────

try:
    _config     = _api_get("/api/config")
    SSP_CONFIGS = _config["ssp_configs"]
    REGIONS     = _config["regions"]
except Exception as exc:
    raise RuntimeError(
        f"Cannot reach IAM backend at {BACKEND_URL}. "
        "Start it first:  python backend/api.py"
    ) from exc

SSP_OPTIONS        = [{"label": v["name"], "value": k} for k, v in SSP_CONFIGS.items()]
REGION_OPTIONS     = [{"label": r, "value": i} for i, r in enumerate(REGIONS)]
ALL_REGION_INDICES = list(range(len(REGIONS)))

# ── constants ──────────────────────────────────────────────────────────────────

REGION_COLORS = [
    "#2a9d8f", "#e9c46a", "#e76f51", "#a8d8ea", "#90be6d",
    "#f4a261", "#c77dff", "#4cc9f0", "#fb8500", "#8338ec", "#06d6a0", "#ff6b6b",
]

BG      = "#0f1623"
SIDEBAR = "#121929"
ACCENT  = "#2a9d8f"
PLOT_BG = "#111827"

TAB_STYLE = {
    "background": "#0a1020", "color": "#4a6a88",
    "border": "none", "borderBottom": "1px solid #1e2d42",
    "padding": "9px 18px", "fontSize": "13px",
}
TAB_SEL = {**TAB_STYLE, "color": ACCENT,
           "borderTop": f"2px solid {ACCENT}", "background": "#161d2e"}

DAMAGE_INFO = {
    "quadratic": "Standard DICE: Ω = ψ₂·T². Small losses at low temps, accelerating above 2–3°C.",
    "linear":    "Proportional to temperature rise. Simpler but may underestimate high-end tail risks.",
    "threshold": "Tipping-point: modest damage below 3 °C, then a sharp jump — models abrupt regime shifts.",
}
WELFARE_INFO = {
    "utilitarian": "Ramsey–Koopmans: uniform damage fraction across all regions. Standard DICE/RICE baseline.",
    "egalitarian": "Poorer regions bear amplified damage (lower adaptive capacity). Damage multiplier scales with inverse √(per-capita GDP), clipped to [0.4×, 3×]. Raises global effective damage and SCC.",
    "rawlsian":    "Social planner cares only about the worst-off region. All regions receive the highest regional damage fraction. Significantly lowers global GDP.",
}
ECONOMY_INFO = {
    "market":  "Fixed savings rate per region from 2015 data (19–43% across regions). Capital accumulates at those fixed rates.",
    "optimal": "Ramsey rule: savings rate converges from market rates toward the golden-rule optimum s*=γδ/(δ+ρ). High-savers (China 43%) decline; low-savers (USA 22%) invest more early. Equalises regional capital returns over ~40 years.",
}
ABOUT_TEXT = [
    ("What is an IAM?",
     "Integrated Assessment Models (IAMs) couple economic growth, energy use, and the physical climate "
     "system into a single framework. They are the primary tool used by the IPCC to connect "
     "greenhouse-gas emissions pathways with temperature outcomes and economic costs."),
    ("SSP Scenarios",
     "Shared Socioeconomic Pathways describe plausible futures for society, economy, and technology. "
     "SSP1 is a sustainable 'green' world; SSP5 is fossil-fuel intensive. They set emission "
     "trajectories that feed directly into the carbon cycle and climate modules."),
    ("Emission Control Rate μ",
     "μ (mu) represents the fraction of potential fossil-fuel emissions that are abated through policy "
     "(e.g. carbon pricing, efficiency standards). μ = 0 means no control; μ = 1 means full "
     "decarbonisation. The cost of abatement follows a convex cost curve (higher μ is "
     "disproportionately expensive)."),
    ("Damage Functions",
     "The damage function translates warming into lost economic output. The standard DICE quadratic "
     "form implies modest losses up to 2 °C but rapid acceleration beyond that. Linear damage is "
     "simpler. Threshold ('tipping-point') damage captures potential abrupt transitions like ice-sheet "
     "collapse or permafrost feedbacks."),
    ("Climate Ensemble",
     "Equilibrium Climate Sensitivity (ECS) — how much the planet warms for a doubling of CO₂ — is "
     "uncertain. Running an ensemble samples ECS from its probability distribution (log-normal, "
     "median ≈ 3 °C, per IPCC AR6), giving a range of temperature trajectories and conveying "
     "deep uncertainty to policymakers."),
    ("Social Cost of Carbon",
     "The SCC is the present value of all future economic damages caused by emitting one additional "
     "tonne of CO₂ today. It is the theoretically correct carbon price in a cost-benefit framework "
     "and is central to regulatory impact analyses worldwide."),
]


# ── helpers ────────────────────────────────────────────────────────────────────

INPUT_STYLE = {
    "background": "#0a1220", "border": "1px solid #243448",
    "color": "#b0c8e0", "borderRadius": "4px",
    "padding": "3px 6px", "fontSize": "12px",
    "outline": "none", "textAlign": "center",
}


def label(text):
    return html.Div(text, className="sidebar-label")


def label_with_input(text, input_id, **input_kwargs):
    return html.Div(
        style={"display": "flex", "justifyContent": "space-between",
               "alignItems": "center", "marginTop": "13px", "marginBottom": "4px"},
        children=[
            html.Span(text, style={"color": "#5a7a98", "fontSize": "10px", "fontWeight": "700",
                                   "textTransform": "uppercase", "letterSpacing": "1px"}),
            dcc.Input(id=input_id, style={**INPUT_STYLE, "width": "60px"}, **input_kwargs),
        ],
    )


def section_head(text, color=ACCENT):
    return html.Div(text, style={
        "color": color, "fontSize": "10px", "fontWeight": "800",
        "textTransform": "uppercase", "letterSpacing": "1.3px",
        "marginTop": "4px", "marginBottom": "8px",
    })


def divider():
    return html.Hr(style={"border": "none", "borderTop": "1px solid #1a2740",
                           "margin": "14px 0 4px"})


def stat_card(title, value, sub, color):
    return html.Div(className="stat-card", style={"borderLeft": f"3px solid {color}"}, children=[
        html.Div(title, className="stat-title"),
        html.Div(value, className="stat-value"),
        html.Div(sub,   className="stat-sub"),
    ])


def stats_row(cards):
    return html.Div(cards, className="stats-row")


def base_fig(height=460):
    fig = go.Figure()
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG, plot_bgcolor=PLOT_BG,
        font={"color": "#b0c8e0", "family": "system-ui, sans-serif", "size": 12},
        legend={"bgcolor": "#161d2e", "bordercolor": "#243448", "borderwidth": 1},
        margin={"l": 60, "r": 30, "t": 50, "b": 50},
        height=height, hovermode="x unified",
    )
    return fig


# ── app layout ─────────────────────────────────────────────────────────────────

app = dash.Dash(__name__, title="IAM Explorer",
                assets_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets"),
                prevent_initial_callbacks="initial_duplicate")

app.layout = html.Div(
    style={"display": "flex", "flexDirection": "column", "height": "100vh", "background": BG},
    children=[

        # header
        html.Div(
            style={
                "background": "#080e1a", "borderBottom": f"2px solid {ACCENT}",
                "padding": "0 24px", "height": "54px",
                "display": "flex", "alignItems": "center", "gap": "14px", "flexShrink": 0,
            },
            children=[
                html.Div("◈", style={"fontSize": "20px", "color": ACCENT, "lineHeight": 1}),
                html.Span("IAM Explorer",
                          style={"fontWeight": "800", "fontSize": "17px", "color": "white"}),
                html.Span("Simplified DICE/RICE Integrated Assessment Model",
                          style={"color": "#3a5570", "fontSize": "12.5px", "marginLeft": "6px"}),
                html.Div(style={"flex": 1}),
            ],
        ),

        # body
        html.Div(style={"display": "flex", "flex": 1, "minHeight": 0, "overflow": "hidden"},
                 children=[

            # ── sidebar ──────────────────────────────────────────────────────
            html.Div(
                id="sidebar",
                style={
                    "width": "285px", "minWidth": "200px", "maxWidth": "520px",
                    "background": SIDEBAR,
                    "padding": "12px 14px 20px",
                    "overflowY": "auto", "overflowX": "hidden",
                    "display": "flex", "flexDirection": "column",
                    "flexShrink": 0,
                },
                children=[

                    section_head("Scenario"),

                    label("SSP Pathway"),
                    dcc.Dropdown(id="ssp", options=SSP_OPTIONS, value="SSP2",
                                 clearable=False, style={"fontSize": "13px"}),

                    label("Simulation Years"),
                    html.Div(
                        style={"display": "flex", "gap": "6px", "alignItems": "center",
                               "marginBottom": "4px"},
                        children=[
                            dcc.Input(id="year-start-input", type="number",
                                      min=2015, max=2095, step=5, value=2015,
                                      style={**INPUT_STYLE, "flex": 1}),
                            html.Span("→", style={"color": "#3a5570", "fontSize": "12px",
                                                   "flexShrink": 0}),
                            dcc.Input(id="year-end-input", type="number",
                                      min=2020, max=2100, step=5, value=2100,
                                      style={**INPUT_STYLE, "flex": 1}),
                        ],
                    ),
                    html.Div(className="slider-wrap", children=[
                        dcc.RangeSlider(
                            id="years", min=2015, max=2100, step=5, value=[2015, 2100],
                            marks={2015: "2015", 2050: "2050", 2075: "2075", 2100: "2100"},
                            tooltip={"placement": "bottom", "always_visible": False},
                        ),
                    ]),

                    divider(),
                    section_head("Climate", "#e9c46a"),

                    label("Damage Function"),
                    dcc.Dropdown(
                        id="damage", clearable=False, value="quadratic",
                        options=[
                            {"label": "Quadratic (standard DICE)",     "value": "quadratic"},
                            {"label": "Linear",                         "value": "linear"},
                            {"label": "Threshold (3 °C tipping point)", "value": "threshold"},
                        ],
                        style={"fontSize": "13px"},
                    ),
                    html.Div(id="damage-info", className="info-box"),

                    label_with_input("Climate Ensemble Members", "ensemble-input",
                                     type="number", min=1, max=30, step=1, value=10),
                    html.Div(className="slider-wrap", children=[
                        dcc.Slider(
                            id="ensemble", min=1, max=30, step=1, value=10,
                            marks={1: "1", 5: "5", 10: "10", 20: "20", 30: "30"},
                            tooltip={"placement": "bottom", "always_visible": False},
                        ),
                    ]),
                    html.Div("More members → wider uncertainty bands. Max 30.",
                             style={"color": "#3a5070", "fontSize": "10.5px",
                                    "marginTop": "2px", "lineHeight": "1.4"}),

                    divider(),
                    section_head("Policy — Emission Control μ", "#e76f51"),

                    html.Div(
                        "μ = fraction of emissions reduced by policy  (0 = none, 1 = full).",
                        style={"color": "#3a5070", "fontSize": "10.5px",
                               "lineHeight": "1.45", "marginBottom": "4px"},
                    ),

                    label_with_input("μ start  (near-term)", "mu-start-input",
                                     type="number", min=0, max=1, step=0.05, value=0.10),
                    html.Div(className="slider-wrap", children=[
                        dcc.Slider(
                            id="mu-start", min=0.0, max=1.0, step=0.05, value=0.10,
                            marks={0: "0", 0.5: "50%", 1: "100%"},
                            tooltip={"placement": "bottom", "always_visible": True},
                        ),
                    ]),

                    label_with_input("μ end  (long-run)", "mu-end-input",
                                     type="number", min=0, max=1, step=0.05, value=0.65),
                    html.Div(className="slider-wrap", children=[
                        dcc.Slider(
                            id="mu-end", min=0.0, max=1.0, step=0.05, value=0.65,
                            marks={0: "0", 0.5: "50%", 1: "100%"},
                            tooltip={"placement": "bottom", "always_visible": True},
                        ),
                    ]),

                    html.Button("↺  Reset to SSP default", id="reset-mu",
                                n_clicks=0, className="reset-btn"),

                    divider(),
                    section_head("Regions", "#90be6d"),

                    html.Div(
                        style={"display": "flex", "gap": "6px", "marginBottom": "8px"},
                        children=[
                            html.Button("All", id="regions-all", n_clicks=0,
                                style={"background": "#1a3228", "border": "1px solid #2a5038",
                                       "color": "#90be6d", "padding": "3px 12px",
                                       "borderRadius": "4px", "fontSize": "11px",
                                       "cursor": "pointer", "flex": 1}),
                            html.Button("None", id="regions-none", n_clicks=0,
                                style={"background": "#2a1e1e", "border": "1px solid #5a2828",
                                       "color": "#e76f51", "padding": "3px 12px",
                                       "borderRadius": "4px", "fontSize": "11px",
                                       "cursor": "pointer", "flex": 1}),
                        ],
                    ),
                    dcc.Checklist(
                        id="regions",
                        options=REGION_OPTIONS,
                        value=ALL_REGION_INDICES,
                        labelStyle={"display": "block", "color": "#a0b8d0",
                                    "fontSize": "12px", "marginBottom": "4px"},
                        inputStyle={"marginRight": "7px", "accentColor": "#90be6d"},
                    ),

                    divider(),
                    section_head("Framework  (Educational)", "#a8d8ea"),

                    label("Welfare Function"),
                    dcc.Dropdown(
                        id="welfare", clearable=False, value="utilitarian",
                        options=[
                            {"label": "Utilitarian / Ramsey",         "value": "utilitarian"},
                            {"label": "Egalitarian (per-capita wt.)", "value": "egalitarian"},
                            {"label": "Rawlsian (worst-off region)",  "value": "rawlsian"},
                        ],
                        style={"fontSize": "13px"},
                    ),
                    html.Div(id="welfare-info", className="info-box"),

                    label("Economy Type"),
                    dcc.Dropdown(
                        id="economy", clearable=False, value="market",
                        options=[
                            {"label": "Market / Neoclassical",    "value": "market"},
                            {"label": "Optimal / Social Planner", "value": "optimal"},
                        ],
                        style={"fontSize": "13px"},
                    ),
                    html.Div(id="economy-info", className="info-box"),

                    # Run button — pinned at bottom via margin-top: auto
                    html.Div(style={"marginTop": "auto", "paddingTop": "16px"}, children=[
                        html.Button("▶  Run Simulation", id="run-btn",
                                    n_clicks=0, className="run-btn"),
                        html.Div("Configure settings above, then click Run.",
                                 style={"color": "#2a4058", "fontSize": "10px",
                                        "textAlign": "center", "marginTop": "6px"}),
                    ]),
                ],
            ),

            # ── sidebar resize handle ─────────────────────────────────────────
            html.Div(id="sidebar-resizer"),

            # ── main content ─────────────────────────────────────────────────
            html.Div(
                style={"flex": 1, "minWidth": 0, "display": "flex",
                       "flexDirection": "column", "overflow": "hidden"},
                children=[
                    # Tab bar — never shrinks
                    html.Div(className="tab-bar-wrap", style={"flexShrink": 0}, children=[
                        dcc.Tabs(
                            id="tabs", value="emissions",
                            style={"background": "#0a1020"},
                            children=[
                                dcc.Tab(label="Emissions",         value="emissions",
                                        style=TAB_STYLE, selected_style=TAB_SEL),
                                dcc.Tab(label="Temperature",       value="temperature",
                                        style=TAB_STYLE, selected_style=TAB_SEL),
                                dcc.Tab(label="Regional",          value="regional",
                                        style=TAB_STYLE, selected_style=TAB_SEL),
                                dcc.Tab(label="Economics",         value="economics",
                                        style=TAB_STYLE, selected_style=TAB_SEL),
                                dcc.Tab(label="CO₂ & Forcing",     value="co2",
                                        style=TAB_STYLE, selected_style=TAB_SEL),
                                dcc.Tab(label="About",             value="about",
                                        style=TAB_STYLE, selected_style=TAB_SEL),
                            ],
                        ),
                    ]),
                    dcc.Store(id="run-store"),
                    dcc.Loading(
                        type="circle", color=ACCENT,
                        # parent_style sizes the Loading wrapper div directly,
                        # so it fills the flex column and tab-content scrolls inside it
                        parent_style={
                            "flex": 1, "minHeight": 0,
                            "overflow": "hidden", "display": "flex",
                            "flexDirection": "column",
                        },
                        children=html.Div(
                            id="tab-content",
                            style={"flex": 1, "overflowY": "auto",
                                   "padding": "16px", "minHeight": 0},
                        ),
                    ),
                ],
            ),
        ]),
    ],
)


# ── reactive sidebar callbacks ─────────────────────────────────────────────────

@callback(
    Output("mu-start",       "value"),
    Output("mu-end",         "value"),
    Output("mu-start-input", "value"),
    Output("mu-end-input",   "value"),
    Input("ssp",             "value"),
    Input("reset-mu",        "n_clicks"),
)
def sync_mu(ssp, _):
    cfg = SSP_CONFIGS[ssp]
    return cfg["mu_start"], cfg["mu_end"], cfg["mu_start"], cfg["mu_end"]


# ── input ↔ slider sync ────────────────────────────────────────────────────────

@callback(
    Output("years", "value"),
    Input("year-start-input", "value"),
    Input("year-end-input",   "value"),
    prevent_initial_call=True,
)
def year_inputs_to_slider(start, end):
    if start is None or end is None:
        raise dash.exceptions.PreventUpdate
    return [int(start), int(end)]


@callback(
    Output("year-start-input", "value", allow_duplicate=True),
    Output("year-end-input",   "value", allow_duplicate=True),
    Input("years", "value"),
    prevent_initial_call=True,
)
def slider_to_year_inputs(years):
    return years[0], years[1]


@callback(
    Output("mu-start", "value", allow_duplicate=True),
    Input("mu-start-input", "value"),
    prevent_initial_call=True,
)
def mu_start_input_to_slider(v):
    if v is None:
        raise dash.exceptions.PreventUpdate
    return round(float(v), 2)


@callback(
    Output("mu-start-input", "value", allow_duplicate=True),
    Input("mu-start", "value"),
    prevent_initial_call=True,
)
def mu_start_slider_to_input(v):
    return v


@callback(
    Output("mu-end", "value", allow_duplicate=True),
    Input("mu-end-input", "value"),
    prevent_initial_call=True,
)
def mu_end_input_to_slider(v):
    if v is None:
        raise dash.exceptions.PreventUpdate
    return round(float(v), 2)


@callback(
    Output("mu-end-input", "value", allow_duplicate=True),
    Input("mu-end", "value"),
    prevent_initial_call=True,
)
def mu_end_slider_to_input(v):
    return v


@callback(
    Output("ensemble", "value", allow_duplicate=True),
    Input("ensemble-input", "value"),
    prevent_initial_call=True,
)
def ensemble_input_to_slider(v):
    if v is None:
        raise dash.exceptions.PreventUpdate
    return int(max(1, min(30, v)))


@callback(
    Output("ensemble-input", "value", allow_duplicate=True),
    Input("ensemble", "value"),
    prevent_initial_call=True,
)
def ensemble_slider_to_input(v):
    return v


@callback(
    Output("regions", "value"),
    Input("regions-all",  "n_clicks"),
    Input("regions-none", "n_clicks"),
    prevent_initial_call=True,
)
def toggle_regions(_, __):
    return ALL_REGION_INDICES if dash.ctx.triggered_id == "regions-all" else []


@callback(Output("damage-info",  "children"), Input("damage",  "value"))
def damage_info(v):  return DAMAGE_INFO[v]

@callback(Output("welfare-info", "children"), Input("welfare", "value"))
def welfare_info(v): return WELFARE_INFO[v]

@callback(Output("economy-info", "children"), Input("economy", "value"))
def economy_info(v): return ECONOMY_INFO[v]


# ── model run — calls backend API on button press only ────────────────────────

@callback(
    Output("run-store", "data"),
    Input("run-btn",  "n_clicks"),
    State("ssp",      "value"),
    State("damage",   "value"),
    State("ensemble", "value"),
    State("years",    "value"),
    State("mu-start", "value"),
    State("mu-end",   "value"),
    State("welfare",  "value"),
    State("economy",  "value"),
    prevent_initial_call=False,
)
def run_model(_, ssp, damage, ensemble, years, mu_start, mu_end, welfare, economy):
    start, end = years
    if start >= end:
        return {"error": "Start year must be before end year."}
    try:
        return _api_post("/api/run", {
            "ssp":      ssp,
            "start":    start,
            "end":      end,
            "damage":   damage,
            "ensemble": int(ensemble),
            "mu_start": float(mu_start),
            "mu_end":   float(mu_end),
            "welfare":  welfare,
            "economy":  economy,
        })
    except urllib.error.URLError:
        return {"error": f"Backend unreachable at {BACKEND_URL}. Is it running?"}
    except Exception as exc:
        return {"error": str(exc)}


# ── tab renderer — reads from store only, never touches the model ──────────────

@callback(
    Output("tab-content", "children"),
    Input("tabs",      "value"),
    Input("run-store", "data"),
    State("regions",   "value"),
)
def render_tab(tab, data, regions):
    if not data:
        return _placeholder()
    if "error" in data:
        return html.Div(data["error"],
                        style={"color": "#e76f51", "padding": "40px", "textAlign": "center"})
    sel = sorted(regions) if regions else []
    yrs = data["years"]
    dispatch = {
        "about":       lambda: _tab_about(),
        "emissions":   lambda: _tab_emissions(data, yrs),
        "temperature": lambda: _tab_temperature(data, yrs),
        "regional":    lambda: _tab_regional(data, yrs, sel),
        "economics":   lambda: _tab_economics(data, yrs, sel),
        "co2":         lambda: _tab_co2(data, yrs),
    }
    return dispatch.get(tab, lambda: html.Div())()


# ── tab content builders ───────────────────────────────────────────────────────

def _placeholder():
    return html.Div(
        style={"display": "flex", "flexDirection": "column", "alignItems": "center",
               "justifyContent": "center", "height": "60vh",
               "color": "#2a4058", "gap": "16px"},
        children=[
            html.Div("◈", style={"fontSize": "40px", "color": "#1a3048"}),
            html.Div("Configure settings in the sidebar, then click",
                     style={"fontSize": "14px"}),
            html.Div("▶  Run Simulation",
                     style={"fontSize": "16px", "color": ACCENT, "fontWeight": "700"}),
        ],
    )


def _tab_emissions(d, yrs):
    glob    = d["global_emissions"]
    mu_mean = [sum(col) / len(col) for col in zip(*d["mu"])]
    mu_pct  = [v * 100 for v in mu_mean]
    enrg    = [sum(r[i] for r in d["emissions"]) for i in range(len(yrs))]

    fig = base_fig()
    fig.add_trace(go.Scatter(x=yrs, y=glob, name="Total emissions",
                             line={"color": ACCENT, "width": 2.5},
                             fill="tozeroy", fillcolor="rgba(42,157,143,0.07)"))
    fig.add_trace(go.Scatter(x=yrs, y=enrg, name="Energy/industrial",
                             line={"color": "#e9c46a", "width": 1.6, "dash": "dot"}))
    fig.add_trace(go.Scatter(x=yrs, y=d["land_emissions"], name="Land-use change",
                             line={"color": "#e76f51", "width": 1.6, "dash": "dash"}))
    fig.add_trace(go.Scatter(x=yrs, y=mu_pct, name="Emission control μ (right)",
                             yaxis="y2",
                             line={"color": "#a8d8ea", "width": 1.2, "dash": "longdash"}))
    fig.update_layout(
        title=f"Global CO₂ Emissions — {d['ssp_name']}",
        xaxis_title="Year", yaxis_title="GtCO₂ / year",
        yaxis2={"title": "Control rate μ (%)", "overlaying": "y", "side": "right",
                "range": [0, 105], "showgrid": False,
                "ticksuffix": "%", "color": "#a8d8ea"},
    )
    peak_i = int(max(range(len(glob)), key=lambda i: glob[i]))
    cum    = sum((glob[i] + glob[i-1]) * 0.5 * (yrs[i] - yrs[i-1]) for i in range(1, len(yrs)))
    return html.Div([
        dcc.Graph(figure=fig, config={"displayModeBar": False}, responsive=True),
        stats_row([
            stat_card("Peak emissions",     f"{glob[peak_i]:.1f} GtCO₂/yr", f"Year {yrs[peak_i]}", "#e9c46a"),
            stat_card("Final year",         f"{glob[-1]:.1f} GtCO₂/yr",     f"Year {yrs[-1]}",     ACCENT),
            stat_card("Cumulative total",   f"{cum:,.0f} GtCO₂",            f"{yrs[0]}–{yrs[-1]}", "#a8d8ea"),
            stat_card("Final control rate", f"{mu_pct[-1]:.0f}%",           "mean across regions", "#e76f51"),
        ]),
    ])


def _tab_temperature(d, yrs):
    n_ens   = d["ensemble_size"]
    ens     = d.get("temperature_ensemble")
    p5, p95 = d["temperature_p5"], d["temperature_p95"]

    fig = base_fig()
    if ens and n_ens <= 20:
        for i in range(n_ens):
            fig.add_trace(go.Scatter(
                x=yrs, y=[row[i] for row in ens],
                line={"color": "rgba(42,157,143,0.18)", "width": 0.8},
                showlegend=False, hoverinfo="skip",
            ))
    fig.add_trace(go.Scatter(
        x=yrs + yrs[::-1], y=p95 + p5[::-1],
        fill="toself", fillcolor="rgba(42,157,143,0.13)",
        line={"color": "rgba(0,0,0,0)"}, name="5–95 % range", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(x=yrs, y=d["temperature_p50"],
                             name="Median (p50)", line={"color": ACCENT, "width": 2.5}))
    fig.add_trace(go.Scatter(x=yrs, y=d["temperature"],
                             name="Ensemble mean",
                             line={"color": "#e9c46a", "width": 1.5, "dash": "dot"}))
    for temp, lbl, col in [(1.5, "Paris 1.5 °C", "#90be6d"),
                           (2.0, "Paris 2 °C",   "#e9c46a"),
                           (3.0, "3 °C threshold","#e76f51")]:
        fig.add_hline(y=temp, line={"color": col, "width": 1, "dash": "dash"},
                      annotation_text=lbl, annotation_position="right",
                      annotation_font={"color": col, "size": 11})
    fig.update_layout(title=f"Global Mean Temperature — {d['ssp_name']}",
                      xaxis_title="Year", yaxis_title="°C above pre-industrial")
    ecs = d["ecs_values"]
    return html.Div([
        dcc.Graph(figure=fig, config={"displayModeBar": False}, responsive=True),
        stats_row([
            stat_card("Median warming (final)", f"{d['temperature_p50'][-1]:.2f} °C",
                      "vs pre-industrial", ACCENT),
            stat_card("90 % range (final)", f"{p5[-1]:.2f}–{p95[-1]:.2f} °C",
                      f"5th–95th pct, {n_ens} members", "#a8d8ea"),
            stat_card("ECS range",   f"{min(ecs):.1f}–{max(ecs):.1f} °C",
                      "equilibrium climate sensitivity", "#e9c46a"),
            stat_card("ECS median",  f"{sorted(ecs)[len(ecs)//2]:.2f} °C",
                      "log-normal per IPCC AR6", "#e76f51"),
        ]),
    ])


def _tab_regional(d, yrs, sel):
    if not sel:
        return html.Div("Select regions in the sidebar to display breakdowns.",
                        style={"color": "#3a5570", "padding": "60px",
                               "textAlign": "center", "fontSize": "14px"})
    fig = base_fig(height=420)
    for idx, ri in enumerate(sel):
        fig.add_trace(go.Scatter(
            x=yrs, y=d["emissions"][ri], name=REGIONS[ri],
            line={"color": REGION_COLORS[idx % len(REGION_COLORS)], "width": 1.5},
            stackgroup="one",
        ))
    fig.update_layout(title="Regional CO₂ Emissions — Energy/Industrial (stacked)",
                      xaxis_title="Year", yaxis_title="GtCO₂ / year")

    fig2 = base_fig(height=280)
    fig2.add_trace(go.Bar(
        x=[REGIONS[ri] for ri in sel],
        y=[d["emissions"][ri][-1] for ri in sel],
        marker_color=[REGION_COLORS[i % len(REGION_COLORS)] for i in range(len(sel))],
        showlegend=False,
    ))
    fig2.update_layout(title=f"Regional Emissions — Year {yrs[-1]}",
                       xaxis_title="Region", yaxis_title="GtCO₂ / year",
                       margin={"l": 60, "r": 30, "t": 45, "b": 60})
    return html.Div([
        dcc.Graph(figure=fig,  config={"displayModeBar": False}, responsive=True),
        dcc.Graph(figure=fig2, config={"displayModeBar": False}, responsive=True),
    ])


def _tab_economics(d, yrs, sel):
    n_reg     = len(d["gdp"])
    gdp_net   = [sum(d["gdp"][r][i]       for r in range(n_reg)) for i in range(len(yrs))]
    gdp_gross = [sum(d["gdp_gross"][r][i]  for r in range(n_reg)) for i in range(len(yrs))]
    mac_mean  = [sum(d["mac"][r][i]        for r in range(n_reg)) / n_reg
                 for i in range(len(yrs))]

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Global Net GDP (trillion USD)", "Global Gross GDP (trillion USD)",
                        "Social Cost of Carbon (USD / tCO₂)",
                        "Mean Marginal Abatement Cost (USD / tCO₂)"),
        vertical_spacing=0.18, horizontal_spacing=0.12,
    )
    for (row, col), (series, color) in zip(
        [(1,1),(1,2),(2,1),(2,2)],
        [(gdp_net, ACCENT), (gdp_gross, "#e9c46a"),
         (d["scc"], "#e76f51"), (mac_mean, "#a8d8ea")],
    ):
        fig.add_trace(go.Scatter(x=yrs, y=series,
                                 line={"color": color}, showlegend=False), row=row, col=col)
    fig.update_layout(
        template="plotly_dark", paper_bgcolor=BG, plot_bgcolor=PLOT_BG,
        font={"color": "#b0c8e0", "size": 12}, height=480, showlegend=False,
        margin={"l": 55, "r": 25, "t": 55, "b": 50}, hovermode="x unified",
    )
    children = [dcc.Graph(figure=fig, config={"displayModeBar": False}, responsive=True)]

    if sel:
        fig2 = base_fig(height=320)
        for idx, ri in enumerate(sel):
            fig2.add_trace(go.Scatter(
                x=yrs, y=d["gdp_per_capita"][ri], name=REGIONS[ri],
                line={"color": REGION_COLORS[idx % len(REGION_COLORS)], "width": 1.6},
            ))
        fig2.update_layout(title="Net GDP per Capita by Region (thousand USD / person)",
                           xaxis_title="Year", yaxis_title="Thousand USD (2015 PPP)")
        children.append(dcc.Graph(figure=fig2, config={"displayModeBar": False}, responsive=True))

    children.append(stats_row([
        stat_card("Global net GDP (final)", f"${gdp_net[-1]:,.0f} T",   "trillion 2015 USD", ACCENT),
        stat_card("Social Cost of Carbon",  f"${d['scc'][-1]:,.0f}",    "USD / tCO₂",        "#e76f51"),
        stat_card("Mean MAC (final)",       f"${mac_mean[-1]:,.1f}",    "USD / tCO₂",        "#a8d8ea"),
    ]))
    return html.Div(children)


def _tab_co2(d, yrs):
    fig = base_fig(height=340)
    fig.add_trace(go.Scatter(x=yrs, y=d["co2_ppm"], name="Atmospheric CO₂",
                             line={"color": "#e76f51", "width": 2.5},
                             fill="tozeroy", fillcolor="rgba(231,111,81,0.07)"))
    for ppm, lbl, col in [(278, "Pre-industrial (278 ppm)", "#90be6d"),
                           (420, "~2023 level (~420 ppm)",   "#e9c46a"),
                           (560, "2× CO₂ (560 ppm)",         "#e76f51")]:
        fig.add_hline(y=ppm, line={"color": col, "width": 1, "dash": "dash"},
                      annotation_text=lbl, annotation_position="right",
                      annotation_font={"color": col, "size": 11})
    fig.update_layout(title="Atmospheric CO₂ Concentration",
                      xaxis_title="Year", yaxis_title="ppm")

    fig2 = base_fig(height=290)
    fig2.add_trace(go.Scatter(x=yrs, y=d["forcing"],
                              name="Total forcing", line={"color": "#a8d8ea", "width": 2}))
    fig2.add_trace(go.Scatter(x=yrs, y=d["f_co2"], name="CO₂ forcing",
                              line={"color": "#e76f51", "width": 1.5, "dash": "dot"}))
    fig2.add_trace(go.Scatter(x=yrs, y=d["f_ex"], name="Exogenous forcing",
                              line={"color": "#e9c46a", "width": 1.5, "dash": "dash"}))
    fig2.update_layout(title="Radiative Forcing",
                       xaxis_title="Year", yaxis_title="W / m²")

    peak_i = int(max(range(len(d["co2_ppm"])), key=lambda i: d["co2_ppm"][i]))
    return html.Div([
        dcc.Graph(figure=fig,  config={"displayModeBar": False}, responsive=True),
        dcc.Graph(figure=fig2, config={"displayModeBar": False}, responsive=True),
        stats_row([
            stat_card("CO₂ (final year)",      f"{d['co2_ppm'][-1]:.0f} ppm",    "",                   "#e76f51"),
            stat_card("Peak CO₂",              f"{d['co2_ppm'][peak_i]:.0f} ppm", f"Year {yrs[peak_i]}","#e9c46a"),
            stat_card("Total forcing (final)", f"{d['forcing'][-1]:.2f} W/m²",   "",                   "#a8d8ea"),
        ]),
    ])


def _tab_about():
    cards = [
        html.Div(style={
            "background": "#161d2e", "borderRadius": "8px",
            "padding": "16px 20px", "marginBottom": "12px",
            "borderLeft": f"3px solid {ACCENT}",
        }, children=[
            html.Div(title, style={"color": ACCENT, "fontWeight": "700",
                                   "fontSize": "13px", "marginBottom": "7px"}),
            html.Div(body,  style={"color": "#7a9ab8", "fontSize": "12.5px",
                                   "lineHeight": "1.65"}),
        ])
        for title, body in ABOUT_TEXT
    ]
    return html.Div(
        style={"maxWidth": "760px", "margin": "0 auto", "paddingTop": "8px"},
        children=[
            html.Div("How scientists and policymakers use IAMs",
                     style={"color": "#b0c8e0", "fontSize": "15px",
                            "fontWeight": "700", "marginBottom": "16px"}),
            *cards,
            html.Div(
                "This model is a simplified RICE/DICE implementation for educational use in ChE 481. "
                "Results are qualitatively representative but should not be used for policy analysis.",
                style={"color": "#2a4058", "fontSize": "11px",
                       "borderTop": "1px solid #1a2740",
                       "paddingTop": "12px", "marginTop": "4px"},
            ),
        ],
    )


# ── entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("IAM_FRONTEND_PORT", 8050))
    app.run(debug=False, port=port)
