from dash import dcc, html

from constants import BG, SIDEBAR, ACCENT, TAB_STYLE, TAB_SEL, INPUT_STYLE, CLIMATE_INFO
from components import label, label_with_input, section_head, divider
from backend_client import SSP_OPTIONS, REGION_OPTIONS, ALL_REGION_INDICES

def build_layout():
    return html.Div(
        style={"display": "flex", "flexDirection": "column", "height": "100vh", "background": BG},
        children=[

            # Header
            html.Div(
                style={
                    "background": "#080e1a", "borderBottom": f"2px solid {ACCENT}",
                    "padding": "0 24px", "height": "54px",
                    "display": "flex", "alignItems": "center", "gap": "14px", "flexShrink": 0,
                },
                children=[
                    html.Span("IAM dying",
                              style={"fontWeight": "800", "fontSize": "22px", "color": "white"}),
                    html.Span("Simplified DICE/RICE Integrated Assessment Model",
                              style={"color": "#9fbcce", "fontSize": "15px", "marginLeft": "6px"}),
                    html.Div(style={"flex": 1}),
                ],
            ),

            # Body
            html.Div(style={"display": "flex", "flex": 1, "minHeight": 0, "overflow": "hidden"},
                     children=[

                # Sidebar
                html.Div(
                    id="sidebar",
                    style={
                        "width": "380px", "minWidth": "200px", "maxWidth": "560px",
                        "background": SIDEBAR,
                        "padding": "12px 14px 20px",
                        "overflowY": "auto", "overflowX": "hidden",
                        "display": "flex", "flexDirection": "column",
                        "flexShrink": 0,
                    },
                    children=[

                        section_head("Scenario"),

                        label("SSP Pathway"),
                        html.Div(
                            html.I("Projected global socioeconomic scenarios, sets development trajectory (population, GDP, technology, climate policy, etc.)"),
                            style={"color": "#9fbcce", "fontSize": "12px",
                                   "lineHeight": "1.45", "marginBottom": "10px"},
                        ),
                        dcc.Dropdown(id="ssp", options=SSP_OPTIONS, value="SSP2",
                                     clearable=False, searchable=False, style={"fontSize": "13px"}),
                        html.Div(id="ssp-info", className="info-box"),

                        html.Div(style={"marginTop": "12px"}),
                        label("Simulation Years"),
                        html.Div(
                            style={"display": "flex", "gap": "6px", "alignItems": "center",
                                   "marginBottom": "4px"},
                            children=[
                                dcc.Input(id="year-start-input", type="number",
                                          min=2015, max=2095, step=5, value=2015,
                                          style={**INPUT_STYLE, "flex": 1}),
                                html.Span("→", style={"color": "#7a9ab8", "fontSize": "12px",
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

                        label("Climate Model"),
                        dcc.Dropdown(
                            id="climate", clearable=False, searchable=False, value="dice",
                            options=[
                                {"label": "DICE 2-box (default)",  "value": "dice"},
                                {"label": "FaIR v2 (full physics)",      "value": "fair"},
                            ],
                            style={"fontSize": "14px"},
                        ),
                        html.Div(id="climate-info", className="info-box"),

                        label("Damage Function"),
                        dcc.Dropdown(
                            id="damage", clearable=False, searchable=False, value="quadratic",
                            options=[
                                {"label": "Quadratic (DICE standard)", "value": "quadratic"},
                                {"label": "Linear", "value": "linear"},
                                {"label": "Threshold (3 °C tipping point)", "value": "threshold"},
                                {"label": "Kalkuhl (rate-of-change, 2019)", "value": "kalkuhl"},
                            ],
                            style={"fontSize": "14px"},
                        ),
                        html.Div(id="damage-info", className="info-box"),

                        label_with_input("Climate Ensemble Members", "ensemble-input",
                                         type="number", min=1, max=30, step=1, value=10),
                        html.Div(
                            html.I("Number of model runs with different ECS samples. More members give more reliable uncertainty band."),
                            style={"color": "#9fbcce", "fontSize": "12px",
                                   "lineHeight": "1.45", "marginBottom": "4px"},
                        ),
                        html.Div(className="slider-wrap", children=[
                            dcc.Slider(
                                id="ensemble", min=1, max=30, step=1, value=10,
                                marks={1: "1", 5: "5", 10: "10", 20: "20", 30: "30"},
                                tooltip={"placement": "bottom", "always_visible": False},
                            ),
                        ]),

                        divider(),
                        section_head("Policy — Emission Control μ", "#e76f51"),

                        html.Div(
                            html.I("Fraction of emissions reduced by policy (0 = none, 1 = full)"),
                            style={"color": "#9fbcce", "fontSize": "12px",
                                   "lineHeight": "1.45", "marginBottom": "4px"},
                        ),

                        label_with_input("μ start", "cr-start-input",
                                         type="number", min=0, max=1, step=0.05, value=0.10),
                        html.Div(className="slider-wrap", children=[
                            dcc.Slider(
                                id="cr-start", min=0.0, max=1.0, step=0.05, value=0.10,
                                marks={0: "0", 0.5: "50%", 1: "100%"},
                                tooltip={"placement": "bottom", "always_visible": True},
                            ),
                        ]),

                        label_with_input("μ end (long-run)", "cr-end-input",
                                         type="number", min=0, max=1, step=0.05, value=0.65),
                        html.Div(className="slider-wrap", children=[
                            dcc.Slider(
                                id="cr-end", min=0.0, max=1.0, step=0.05, value=0.65,
                                marks={0: "0", 0.5: "50%", 1: "100%"},
                                tooltip={"placement": "bottom", "always_visible": True},
                            ),
                        ]),

                        html.Button("↺  Reset to Default", id="reset-cr",
                                    n_clicks=0, className="reset-btn"),

                        divider(),
                        section_head("Regions", "#90be6d"),

                        html.Div(
                            style={"display": "flex", "gap": "6px", "marginBottom": "8px"},
                            children=[
                                html.Button("All", id="regions-all", n_clicks=0,
                                    style={"background": "#1a3228", "border": "1px solid #2a5038",
                                           "color": "#90be6d", "padding": "3px 12px",
                                           "borderRadius": "0", "fontSize": "12px",
                                           "cursor": "pointer", "flex": 1}),
                                html.Button("None", id="regions-none", n_clicks=0,
                                    style={"background": "#2a1e1e", "border": "1px solid #5a2828",
                                           "color": "#e76f51", "padding": "3px 12px",
                                           "borderRadius": "0", "fontSize": "12px",
                                           "cursor": "pointer", "flex": 1}),
                            ],
                        ),
                        dcc.Checklist(
                            id="regions",
                            options=REGION_OPTIONS,
                            value=ALL_REGION_INDICES,
                            labelStyle={"display": "block", "color": "#b8cce0",
                                        "fontSize": "13px", "marginBottom": "4px"},
                            inputStyle={"marginRight": "7px", "accentColor": "#90be6d"},
                        ),

                        divider(),
                        section_head("Region-Specific", "#a8d8ea"),

                        label("Welfare Function"),
                        dcc.Dropdown(
                            id="welfare", clearable=False, searchable=False, value="utilitarian",
                            options=[
                                {"label": "Utilitarian (standard DICE)",        "value": "utilitarian"},
                                {"label": "Prioritarian (rank-weighted)",        "value": "prioritarian"},
                                {"label": "Sufficientarian (sufficiency floor)", "value": "sufficientarian"},
                                {"label": "Egalitarian (Gini-weighted)",         "value": "egalitarian"},
                            ],
                            style={"fontSize": "14px"},
                        ),
                        html.Div(id="welfare-info", className="info-box"),

                        label("Economy Type"),
                        dcc.Dropdown(
                            id="economy", clearable=False, searchable=False, value="market",
                            options=[
                                {"label": "Market / Neoclassical",    "value": "market"},
                                {"label": "Optimal / Social Planner", "value": "optimal"},
                            ],
                            style={"fontSize": "14px"},
                        ),
                        html.Div(id="economy-info", className="info-box"),

                        # Run button — pinned at bottom via margin-top: auto
                        html.Div(style={"marginTop": "auto", "paddingTop": "16px"}, children=[
                            html.Button("▶  Run Simulation", id="run-btn",
                                        n_clicks=0, className="run-btn")
                        ]),
                    ],
                ),

                # Sidebar resize handle
                html.Div(id="sidebar-resizer"),

                # Main screen
                html.Div(
                    style={"flex": 1, "minWidth": 0, "display": "flex",
                           "flexDirection": "column", "overflow": "hidden"},
                    children=[
                        html.Div(className="tab-bar-wrap", style={"flexShrink": 0}, children=[
                            dcc.Tabs(
                                id="tabs", value="emissions",
                                style={"background": "#0a1020"},
                                children=[
                                    dcc.Tab(label="Global Emissions",   value="emissions",
                                            style=TAB_STYLE, selected_style=TAB_SEL),
                                    dcc.Tab(label="Regional Emissions", value="regional",
                                            style=TAB_STYLE, selected_style=TAB_SEL),
                                    dcc.Tab(label="Temperature",        value="temperature",
                                            style=TAB_STYLE, selected_style=TAB_SEL),
                                    dcc.Tab(label="Economics",     value="economics",
                                            style=TAB_STYLE, selected_style=TAB_SEL),
                                    dcc.Tab(label="CO₂ & Forcing", value="co2",
                                            style=TAB_STYLE, selected_style=TAB_SEL),
                                    dcc.Tab(label="Welfare & Damages", value="welfare",
                                            style=TAB_STYLE, selected_style=TAB_SEL),
                                    dcc.Tab(label="About",         value="about",
                                            style=TAB_STYLE, selected_style=TAB_SEL),
                                ],
                            ),
                        ]),
                        dcc.Store(id="run-store"),
                        dcc.Loading(
                            type="circle", color=ACCENT,
                            parent_style={
                                "flex": 1, "minHeight": 0,
                                "overflow": "hidden", "display": "flex",
                                "flexDirection": "column",
                            },
                            children=html.Div(
                                id="tab-content",
                                style={"flex": 1, "overflowY": "auto",
                                       "padding": "20px 90px", "minHeight": 0},
                            ),
                        ),
                    ],
                ),
            ]),
        ],
    )