from dash import dcc, html
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from constants import ACCENT, BG, PLOT_BG, REGION_COLORS, ABOUT_TEXT
from components import base_fig, stat_card, stats_row
from backend_client import REGIONS

def placeholder():
    return html.Div(
        style={"display": "flex", "flexDirection": "column", "alignItems": "center",
               "justifyContent": "center", "height": "60vh",
               "color": "#7a9ab8", "gap": "16px"},
        children=[
            html.Div("◈", style={"fontSize": "40px", "color": "#4a6a8a"}),
            html.Div("Configure settings in the sidebar, then click",
                     style={"fontSize": "14px"}),
            html.Div("▶  Run Simulation",
                     style={"fontSize": "16px", "color": ACCENT, "fontWeight": "700"}),
        ],
    )

def tab_emissions(d, yrs):
    glob    = d["global_emissions"]
    cr_mean = [sum(col) / len(col) for col in zip(*d["cr"])]
    cr_pct  = [v * 100 for v in cr_mean]
    enrg    = [sum(r[i] for r in d["emissions"]) for i in range(len(yrs))]

    fig = base_fig()
    fig.add_trace(go.Scatter(x=yrs, y=glob, name="Total emissions",
                             line={"color": ACCENT, "width": 2.5},
                             fill="tozeroy", fillcolor="rgba(42,157,143,0.07)"))
    fig.add_trace(go.Scatter(x=yrs, y=enrg, name="Energy/industrial",
                             line={"color": "#e9c46a", "width": 1.6, "dash": "dot"}))
    fig.add_trace(go.Scatter(x=yrs, y=d["land_emissions"], name="Land-use change",
                             line={"color": "#e76f51", "width": 1.6, "dash": "dash"}))
    fig.add_trace(go.Scatter(x=yrs, y=cr_pct, name="Emission control μ (right)",
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
            stat_card("Final control rate", f"{cr_pct[-1]:.0f}%",           "mean across regions", "#e76f51"),
        ]),
    ])


def tab_temperature(d, yrs):
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
                      xaxis_title="Year", yaxis_title="°C above pre-industrial",
                      legend={"x": 0.01, "y": 0.99, "xanchor": "left", "yanchor": "top"})
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


def tab_regional(d, yrs, sel):
    if not sel:
        return html.Div("Select regions in the sidebar to display breakdowns.",
                        style={"color": "#7a9ab8", "padding": "60px",
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


def tab_economics(d, yrs, sel):
    n_reg     = len(d["gdp"])
    gdp_net   = [sum(d["gdp"][r][i]      for r in range(n_reg)) for i in range(len(yrs))]
    gdp_gross = [sum(d["gdp_gross"][r][i] for r in range(n_reg)) for i in range(len(yrs))]
    mac_mean  = [sum(d["mac"][r][i]       for r in range(n_reg)) / n_reg
                 for i in range(len(yrs))]

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Global Net GDP (trillion USD)", "Global Gross GDP (trillion USD)",
                        "Social Cost of Carbon (USD / tCO₂)",
                        "Mean Marginal Abatement Cost (USD / tCO₂)"),
        vertical_spacing=0.18, horizontal_spacing=0.12,
    )
    for (row, col), (series, color, name) in zip(
        [(1,1),(1,2),(2,1),(2,2)],
        [(gdp_net, ACCENT, "Net GDP"),
         (gdp_gross, "#e9c46a", "Gross GDP"),
         (d["scc"], "#e76f51", "SCC"),
         (mac_mean, "#a8d8ea", "MAC")],
    ):
        fig.add_trace(go.Scatter(x=yrs, y=series, name=name,
                                 line={"color": color}, showlegend=False), row=row, col=col)
    fig.update_layout(
        template="plotly_dark", paper_bgcolor=BG, plot_bgcolor=PLOT_BG,
        font={"color": "#b0c8e0", "size": 12, "family": "Cambria Math, Cambria, serif"}, height=480, showlegend=False,
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


def tab_co2(d, yrs):
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
                       xaxis_title="Year", yaxis_title="W / m²",
                       legend={"x": 0.01, "y": 0.99, "xanchor": "left", "yanchor": "top"})

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


def tab_about():
    cards = [
        html.Div(style={
            "background": "#161d2e",
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
            html.Div("Context",
                     style={"color": "#b0c8e0", "fontSize": "15px",
                            "fontWeight": "700", "marginBottom": "16px"}),
            *cards,
        ],
    )
