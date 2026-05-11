import urllib.error

import dash
from dash import html, Input, Output, State, callback

from constants import DAMAGE_INFO, WELFARE_INFO, ECONOMY_INFO, CLIMATE_INFO, SSP_INFO
from backend_client import (
    SSP_CONFIGS, ALL_REGION_INDICES, BACKEND_URL, _api_post,
)
from tabs import (
    placeholder, tab_emissions, tab_temperature,
    tab_regional, tab_economics, tab_co2, tab_welfare, tab_about,
)

@callback(
    Output("cr-start",       "value"),
    Output("cr-end",         "value"),
    Output("cr-start-input", "value"),
    Output("cr-end-input",   "value"),
    Input("ssp",             "value"),
    Input("reset-cr",        "n_clicks"),
)
def sync_cr(ssp, _):
    cfg = SSP_CONFIGS[ssp]
    return cfg["cr_start"], cfg["cr_end"], cfg["cr_start"], cfg["cr_end"]

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
    Output("cr-start", "value", allow_duplicate=True),
    Input("cr-start-input", "value"),
    prevent_initial_call=True,
)
def cr_start_input_to_slider(v):
    if v is None:
        raise dash.exceptions.PreventUpdate
    return round(float(v), 2)

@callback(
    Output("cr-start-input", "value", allow_duplicate=True),
    Input("cr-start", "value"),
    prevent_initial_call=True,
)
def cr_start_slider_to_input(v):
    return v

@callback(
    Output("cr-end", "value", allow_duplicate=True),
    Input("cr-end-input", "value"),
    prevent_initial_call=True,
)
def cr_end_input_to_slider(v):
    if v is None:
        raise dash.exceptions.PreventUpdate
    return round(float(v), 2)

@callback(
    Output("cr-end-input", "value", allow_duplicate=True),
    Input("cr-end", "value"),
    prevent_initial_call=True,
)
def cr_end_slider_to_input(v):
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

@callback(Output("ssp-info",     "children"), Input("ssp",     "value"))
def ssp_info(v):    return SSP_INFO.get(v, "")

@callback(Output("damage-info",  "children"), Input("damage",  "value"))
def damage_info(v):  return DAMAGE_INFO.get(v, "")

@callback(Output("welfare-info", "children"), Input("welfare", "value"))
def welfare_info(v): return WELFARE_INFO.get(v, "")

@callback(Output("economy-info", "children"), Input("economy", "value"))
def economy_info(v): return ECONOMY_INFO.get(v, "")

@callback(Output("climate-info", "children"), Input("climate", "value"))
def climate_info(v): return CLIMATE_INFO.get(v, "")

@callback(
    Output("run-store", "data"),
    Input("run-btn",  "n_clicks"),
    State("ssp",      "value"),
    State("damage",   "value"),
    State("ensemble", "value"),
    State("years",    "value"),
    State("cr-start", "value"),
    State("cr-end",   "value"),
    State("welfare",  "value"),
    State("economy",  "value"),
    State("climate",  "value"),
    prevent_initial_call=False,
)
def run_model(_, ssp, damage, ensemble, years, cr_start, cr_end, welfare, economy, climate):
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
            "cr_start": float(cr_start),
            "cr_end":   float(cr_end),
            "welfare":  welfare,
            "economy":  economy,
            "climate":  climate or "dice",
        })
    except urllib.error.URLError:
        return {"error": f"Backend unreachable at {BACKEND_URL}. Is it running?"}
    except Exception as exc:
        return {"error": str(exc)}

@callback(
    Output("tab-content", "children"),
    Input("tabs",      "value"),
    Input("run-store", "data"),
    State("regions",   "value"),
)
def render_tab(tab, data, regions):
    if tab == "about":
        return tab_about()
    if not data:
        return placeholder()
    if "error" in data:
        return html.Div(data["error"],
                        style={"color": "#e76f51", "padding": "40px", "textAlign": "center"})
    sel = sorted(regions) if regions else []
    yrs = data["years"]
    dispatch = {
        "about":       lambda: tab_about(),
        "emissions":   lambda: tab_emissions(data, yrs),
        "temperature": lambda: tab_temperature(data, yrs),
        "regional":    lambda: tab_regional(data, yrs, sel),
        "economics":   lambda: tab_economics(data, yrs, sel),
        "co2":         lambda: tab_co2(data, yrs),
        "welfare":     lambda: tab_welfare(data, yrs, sel),
    }
    return dispatch.get(tab, lambda: html.Div())()