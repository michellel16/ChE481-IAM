from dash import dcc, html
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from constants import ACCENT, BG, PLOT_BG, REGION_COLORS, ABOUT_TEXT
from components import base_fig, stat_card, stats_row, summary_box
from backend_client import REGIONS

_CONTEXT_STYLE = {
    "color": "#b0c8e0", "fontSize": "14px", "lineHeight": "1.6",
    "marginBottom": "14px",
}

def _ctx(text):
    return html.Div(text, style=_CONTEXT_STYLE)

def placeholder():
    return html.Div(
        style={"display": "flex", "flexDirection": "column", "alignItems": "center",
               "justifyContent": "center", "height": "60vh",
               "color": "#9fbcce", "gap": "16px"},
        children=[
            html.Div("◈", style={"fontSize": "40px", "color": "#6a8aaa"}),
            html.Div("Configure settings in the sidebar, then click",
                     style={"fontSize": "15px"}),
            html.Div("▶  Run Simulation",
                     style={"fontSize": "17px", "color": ACCENT, "fontWeight": "700"}),
        ],
    )

def tab_emissions(d, yrs):
    glob    = d["global_emissions"]
    cr_mean = [sum(col) / len(col) for col in zip(*d["cr"])]
    cr_pct  = [v * 100 for v in cr_mean]
    enrg    = [sum(r[i] for r in d["emissions"]) for i in range(len(yrs))]

    fig = base_fig()
    fig.add_trace(go.Scatter(x=yrs, y=glob, name="Total Emissions",
                             line={"color": ACCENT, "width": 2.5},
                             fill="tozeroy", fillcolor="rgba(42,157,143,0.07)",
                             hovertemplate="Total Emissions: %{y:.2f} GtCO₂/yr<extra></extra>"))
    fig.add_trace(go.Scatter(x=yrs, y=enrg, name="Energy/Industrial",
                             line={"color": "#e9c46a", "width": 1.6, "dash": "dot"},
                             hovertemplate="Energy/Industrial: %{y:.2f} GtCO₂/yr<extra></extra>"))
    fig.add_trace(go.Scatter(x=yrs, y=d["land_emissions"], name="Land-use",
                             line={"color": "#e76f51", "width": 1.6, "dash": "dash"},
                             hovertemplate="Land-Use: %{y:.2f} GtCO₂/yr<extra></extra>"))
    fig.add_trace(go.Scatter(x=yrs, y=cr_pct, name="Emission Control Rate μ",
                             yaxis="y2",
                             line={"color": "#a8d8ea", "width": 1.2, "dash": "longdash"},
                             hovertemplate="Emission Control Rate μ: %{y:.2f}%<extra></extra>"))
    fig.update_layout(
        title=f"Global CO₂ Emissions — {d['ssp_name']}",
        xaxis_title="Year", yaxis_title="GtCO₂/year",
        yaxis2={"title": {"text": "Emissions Control Rate μ (%)", "standoff": 12},
                "overlaying": "y", "side": "right",
                "range": [-8, 105], "showgrid": False, "ticksuffix": "%",
                "color": "#a8d8ea",
                "showline": True, "linecolor": "#607898",
                "ticks": "outside", "ticklen": 16},
        margin={"r": 80},
        hoverlabel={"namelength": -1},
    )
    peak_i = int(max(range(len(glob)), key=lambda i: glob[i]))
    cum    = sum((glob[i] + glob[i-1]) * 0.5 * (yrs[i] - yrs[i-1]) for i in range(1, len(yrs)))
    return html.Div([
        _ctx(
            "Global CO₂ emissions track the total warming forcing the climate system receives "
            "from human activity. The emission control rate μ (right axis) shows the fraction "
            "of industrial emissions being abated — raising μ suppresses emissions but increases "
            "abatement costs. Peak emissions and cumulative totals are the primary drivers of "
            "long-run temperature outcomes: carbon dioxide lingers in the atmosphere for centuries, "
            "so early action prevents irreversible lock-in of warming."
        ),
        dcc.Graph(figure=fig, config={"displayModeBar": False}, responsive=True, style={"height": "600px"}),
        summary_box([
            ("Peak Emissions", f"{glob[peak_i]:.2f} GtCO₂/yr", f"({yrs[peak_i]})"),
            ("Final Year Emissions", f"{glob[-1]:.2f} GtCO₂/yr", f"({yrs[-1]})"),
            ("Cumulative Emissions", f"{cum:,.0f} GtCO₂", f"({yrs[0]}–{yrs[-1]})"),
            ("Final Control Rate", f"{cr_pct[-1]:.0f}%", "(regional mean)"),
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
                             name="Median (p50)", line={"color": ACCENT, "width": 2.5},
                             hovertemplate="Median: %{y:.2f} °C<extra></extra>"))
    fig.add_trace(go.Scatter(x=yrs, y=d["temperature"],
                             name="Ensemble Mean",
                             line={"color": "#e9c46a", "width": 1.5, "dash": "dot"},
                             hovertemplate="Ensemble Mean: %{y:.2f} °C<extra></extra>"))
    for temp, lbl, col in [(1.5, "1.5°C (Paris-Climate Agreement)", "#90be6d"),
                           (2.0, "2°C (Paris-Climate Agreement)", "#e9c46a"),
                           (3.0, "3°C Threshold","#e76f51")]:
        fig.add_hline(y=temp, line={"color": col, "width": 1, "dash": "dash"},
                      annotation_text=lbl, annotation_position="right",
                      annotation_font={"color": col, "size": 12})
    fig.update_layout(title=f"Global Mean Temperature — {d['ssp_name']}",
                      xaxis_title="Year", yaxis_title="°C Above Pre-Industrial Temperature",
                      legend={"x": 0.01, "y": 0.99, "xanchor": "left", "yanchor": "top"})
    ecs = d["ecs_values"]
    return html.Div([
        _ctx(
            "Global mean temperature rise above pre-industrial levels is the central output of "
            "the climate system. The ensemble spread reflects uncertainty in equilibrium climate "
            "sensitivity (ECS) — the long-run warming from a doubling of CO₂. The IPCC AR6 "
            "estimates ECS at 2.5–4°C (likely range). Paris Agreement targets (1.5°C and 2°C) "
            "are shown as reference lines; exceeding these thresholds risks activating climate "
            "tipping points and non-linear damage regimes that standard damage functions do not "
            "capture. Even if median outcomes are acceptable, the upper tail of the ensemble "
            "represents genuine catastrophic risk — the scientific case for precautionary policy."
        ),
        dcc.Graph(figure=fig, config={"displayModeBar": False}, responsive=True, style={"height": "600px"}),
        summary_box([
            ("Final Median Warming", f"{d['temperature_p50'][-1]:.2f} °C", "vs Pre-Industrial"),
            ("Warming In 90 % Range", f"{p5[-1]:.2f}–{p95[-1]:.2f} °C", f"({n_ens} Ensemble Members)"),
            ("Equilibrium Climate Sensitivity Range", f"{min(ecs):.2f}–{max(ecs):.2f} °C", ""),
            ("Equilibrium Climate Sensitivity Median", f"{sorted(ecs)[len(ecs)//2]:.2f} °C", ""),
        ]),
    ])

def tab_regional(d, yrs, sel):
    if not sel:
        return html.Div("Select regions in sidebar.",
                        style={"color": "#9fbcce", "padding": "60px",
                               "textAlign": "center", "fontSize": "15px"})
    fig = base_fig(height=600)
    for idx, ri in enumerate(sel):
        fig.add_trace(go.Scatter(
            x=yrs, y=d["emissions"][ri], name=REGIONS[ri],
            line={"color": REGION_COLORS[idx % len(REGION_COLORS)], "width": 1.5},
            stackgroup="one",
            hovertemplate=f"{REGIONS[ri]}: %{{y:.2f}} GtCO₂/yr<extra></extra>",
        ))
    fig.update_layout(title="Regional CO₂ Emissions — Energy/Industrial",
                      xaxis_title="Year", yaxis_title="GtCO₂ / year")

    fig2 = base_fig(height=600)
    fig2.add_trace(go.Bar(
        x=[REGIONS[ri] for ri in sel],
        y=[d["emissions"][ri][-1] for ri in sel],
        marker_color=[REGION_COLORS[i % len(REGION_COLORS)] for i in range(len(sel))],
        showlegend=False,
        hovertemplate="%{x}: %{y:.2f} GtCO₂/yr<extra></extra>",
    ))
    fig2.update_layout(title=f"Regional Emissions Breakdown in {yrs[-1]}",
                       xaxis_title="Region", yaxis_title="GtCO₂ / year",
                       margin={"l": 60, "r": 30, "t": 45, "b": 60})
    return html.Div([
        _ctx(
            "Regional emissions disaggregate global totals into the model's 12 geographic units. "
            "The stacked area chart shows each region's contribution to total industrial/energy CO₂ "
            "— the baseline trajectory is set by the chosen SSP, while the emission control rate μ "
            "applies across regions. The bar chart shows the regional breakdown in the final year, "
            "revealing where emissions are concentrated and how the distribution evolves over time. "
            "Regional disparities reflect differences in economic scale, energy intensity, and "
            "population — key inputs to both the damage assessment and equity debates."
        ),
        dcc.Graph(figure=fig,  config={"displayModeBar": False}, responsive=True, style={"height": "600px"}),
        dcc.Graph(figure=fig2, config={"displayModeBar": False}, responsive=True, style={"height": "600px"}),
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
                        "Social Cost of Carbon (USD/tCO₂)",
                        "Mean Marginal Abatement Cost (USD/tCO₂)"),
        vertical_spacing=0.26, horizontal_spacing=0.14,
    )
    for (row, col), (series, color, name, htpl) in zip(
        [(1,1),(1,2),(2,1),(2,2)],
        [(gdp_net,  ACCENT, "Net GDP", "Net GDP: %{y:.2f} T USD<extra></extra>"),
         (gdp_gross, "#e9c46a", "Gross GDP", "Gross GDP: %{y:.2f} T USD<extra></extra>"),
         (d["scc"], "#e76f51", "SCC",  "SCC: $%{y:.2f} / tCO₂<extra></extra>"),
         (mac_mean, "#a8d8ea", "MAC", "MAC: $%{y:.2f} / tCO₂<extra></extra>")],
    ):
        fig.add_trace(go.Scatter(x=yrs, y=series, name=name,
                                 line={"color": color}, showlegend=False,
                                 hovertemplate=htpl), row=row, col=col)
    fig.update_layout(
        template="plotly_dark", paper_bgcolor=BG, plot_bgcolor=PLOT_BG,
        font={"color": "#b0c8e0", "size": 13, "family": "Cambria Math, Cambria, serif"}, height=840, showlegend=False,
        margin={"l": 80, "r": 50, "t": 80, "b": 65}, hovermode="x unified",
    )
    fig.update_xaxes(showline=True, linecolor="#607898", linewidth=1, mirror=True,
                     ticks="outside", ticklen=16, title_text="Year")
    fig.update_yaxes(showline=True, linecolor="#607898", linewidth=1, mirror=True,
                     ticks="outside", ticklen=16)
    fig.update_yaxes(title_text="Trillion USD", row=1, col=1)
    fig.update_yaxes(title_text="Trillion USD", row=1, col=2)
    fig.update_yaxes(title_text="USD / tCO₂",   row=2, col=1)
    fig.update_yaxes(title_text="USD / tCO₂",   row=2, col=2)
    fig.update_annotations(font_size=19, yshift=14)
    children = [
        _ctx(
            "The economics tab shows the fundamental tradeoff at the heart of climate-economy "
            "analysis. Net GDP reflects gross output minus climate damages and abatement costs — "
            "the core tension in cost-benefit climate policy. The Social Cost of Carbon (SCC) is "
            "the policy-critical metric: when the marginal abatement cost (MAC) is below the SCC, "
            "further emissions reduction is welfare-improving; when the MAC exceeds the SCC, "
            "additional abatement costs more than the avoided damage it prevents. "
            "Higher emission control rates μ depress near-term GDP but raise long-run GDP by "
            "avoiding climate damages — the magnitude of this tradeoff depends critically on the "
            "damage function and discount rate assumptions."
        ),
        dcc.Graph(figure=fig, config={"displayModeBar": False}, responsive=True, style={"height": "840px"}),
    ]

    if sel:
        fig2 = base_fig(height=600)
        for idx, ri in enumerate(sel):
            fig2.add_trace(go.Scatter(
                x=yrs, y=d["gdp_per_capita"][ri], name=REGIONS[ri],
                line={"color": REGION_COLORS[idx % len(REGION_COLORS)], "width": 1.6},
                hovertemplate=f"{REGIONS[ri]}: %{{y:.2f}} k USD<extra></extra>",
            ))
        fig2.update_layout(title="Net GDP Per Capita by Region (thousand USD/person)",
                           xaxis_title="Year", yaxis_title="Thousand USD")
        children.append(dcc.Graph(figure=fig2, config={"displayModeBar": False}, responsive=True, style={"height": "600px"}))

    children.append(summary_box([
        ("Final Global Net GDP", f"${gdp_net[-1]:,.2f} T", ""),
        ("Social Cost of Carbon", f"${d['scc'][-1]:,.2f}", "USD/tCO₂"),
        ("Final Mean MAC", f"${mac_mean[-1]:,.2f}","USD/tCO₂"),
    ]))
    return html.Div(children)


def tab_co2(d, yrs):
    fig = base_fig(height=600)
    fig.add_trace(go.Scatter(x=yrs, y=d["co2_ppm"], name="Atmospheric CO₂",
                             line={"color": "#e76f51", "width": 2.5},
                             fill="tozeroy", fillcolor="rgba(231,111,81,0.07)",
                             hovertemplate="%{y:.2f} ppm<extra></extra>"))
    for ppm, lbl, col in [(278, "Pre-Industrial (278 ppm)", "#90be6d"),
                           (423, "2023 (423 ppm)", "#e9c46a")]:
        fig.add_hline(y=ppm, line={"color": col, "width": 1, "dash": "dash"},
                      annotation_text=lbl, annotation_position="right",
                      annotation_font={"color": col, "size": 12})
    fig.update_layout(title="Atmospheric CO₂ Concentration",
                      xaxis_title="Year", yaxis_title="ppm")

    fig2 = base_fig(height=600)
    fig2.add_trace(go.Scatter(x=yrs, y=d["forcing"],
                              name="Total Forcing", line={"color": "#a8d8ea", "width": 2},
                              hovertemplate="Total Forcing: %{y:.2f} W/m²<extra></extra>"))
    fig2.add_trace(go.Scatter(x=yrs, y=d["f_co2"], name="CO₂ forcing",
                              line={"color": "#e76f51", "width": 1.5, "dash": "dot"},
                              hovertemplate="CO₂ Forcing: %{y:.2f} W/m²<extra></extra>"))
    fig2.add_trace(go.Scatter(x=yrs, y=d["f_ex"], name="Exogenous Forcing",
                              line={"color": "#e9c46a", "width": 1.5, "dash": "dash"},
                              hovertemplate="Exogenous Forcing: %{y:.2f} W/m²<extra></extra>"))
    fig2.update_layout(title="Radiative Forcing",
                       xaxis_title="Year", yaxis_title="W/m²",
                       legend={"x": 0.01, "y": 0.99, "xanchor": "left", "yanchor": "top"})

    peak_i = int(max(range(len(d["co2_ppm"])), key=lambda i: d["co2_ppm"][i]))
    return html.Div([
        _ctx(
            "Atmospheric CO₂ concentration (ppm) is the primary driver of radiative forcing — "
            "the net energy imbalance warming the planet. Pre-industrial CO₂ was ~278 ppm; "
            "2023 levels reached ~423 ppm, already well above any level seen in 800,000 years of "
            "ice-core records. Total radiative forcing (W/m²) combines CO₂ with non-CO₂ "
            "greenhouse gases and exogenous factors (aerosols, solar). Because CO₂ persists in "
            "the atmosphere for centuries, even reaching net-zero emissions does not immediately "
            "stop warming — it only stops the acceleration. This makes peak CO₂ concentration "
            "a more policy-relevant indicator than the annual emissions rate."
        ),
        dcc.Graph(figure=fig,  config={"displayModeBar": False}, responsive=True, style={"height": "600px"}),
        dcc.Graph(figure=fig2, config={"displayModeBar": False}, responsive=True, style={"height": "600px"}),
        summary_box([
            ("Final CO₂ ppm", f"{d['co2_ppm'][-1]:.0f} ppm", f"({yrs[-1]})"),
            ("Peak CO₂ ppm", f"{d['co2_ppm'][peak_i]:.0f} ppm", f"({yrs[peak_i]})"),
            ("Total Radiative Forcing", f"{d['forcing'][-1]:.2f} W/m²", ""),
        ]),
    ])

def tab_welfare(d, yrs, sel):
    welfare_type = d.get("welfare_type", "utilitarian")
    welfare_labels = {
        "utilitarian":     "Utilitarian",
        "prioritarian":    "Prioritarian",
        "sufficientarian": "Sufficientarian",
        "egalitarian":     "Egalitarian",
    }
    w_label = welfare_labels.get(welfare_type, welfare_type.capitalize())

    dmg_frac = d.get("regional_damage_frac", [])   # list of lists: [region][time]
    gini = d.get("gini_per_year", [])
    n_dmg_regions = len(dmg_frac)

    if not dmg_frac:
        return html.Div("Run the simulation to see welfare & damage graphs.",
                        style={"color": "#9fbcce", "padding": "60px",
                               "textAlign": "center", "fontSize": "15px"})

    # --- 1. Regional damage fraction over time ---
    fig1 = base_fig(height=600)
    regions_to_show = [ri for ri in (sel if sel else list(range(n_dmg_regions)))
                       if ri < n_dmg_regions]
    for idx, ri in enumerate(regions_to_show):
        fig1.add_trace(go.Scatter(
            x=yrs, y=[row * 100 for row in dmg_frac[ri]],
            name=REGIONS[ri],
            line={"color": REGION_COLORS[idx % len(REGION_COLORS)], "width": 1.8},
            hovertemplate=f"{REGIONS[ri]}: %{{y:.2f}}%<extra></extra>",
        ))

    if welfare_type != "utilitarian":
        global_dmg = [
            sum(dmg_frac[r][t] for r in range(len(dmg_frac))) / len(dmg_frac)
            for t in range(len(yrs))
        ]
        fig1.add_trace(go.Scatter(
            x=yrs, y=[v * 100 for v in global_dmg],
            name="Uniform Baseline",
            line={"color": "#ffffff", "width": 1.2, "dash": "dot"},
            hovertemplate="Uniform Baseline: %{y:.2f}%<extra></extra>",
        ))
    fig1.update_layout(
        title=f"Regional Damage Fraction — {w_label}",
        xaxis_title="Year", yaxis_title="Damage (% of Gross Output)",
    )

    last_t = len(yrs) - 1
    uniform_last = sum(dmg_frac[r][last_t] for r in range(n_dmg_regions)) / n_dmg_regions
    multipliers = [
        (dmg_frac[ri][last_t] / uniform_last if uniform_last > 1e-9 else 1.0)
        for ri in regions_to_show
    ]
    colors = ["#a8d8ea" if welfare_type == "utilitarian"
              else ("#e76f51" if m > 1.0 else "#90be6d")
              for m in multipliers]
    fig2 = base_fig(height=380)
    fig2.add_trace(go.Bar(
        x=[REGIONS[ri] for ri in regions_to_show],
        y=multipliers,
        marker_color=colors,
        showlegend=False,
        hovertemplate="%{x}: %{y:.2f}× uniform<extra></extra>",
    ))
    fig2.add_hline(y=1.0, line={"color": "#ffffff", "width": 1, "dash": "dash"},
                   annotation_text="Uniform (utilitarian)",
                   annotation_position="right",
                   annotation_font={"color": "#ffffff", "size": 12})
    fig2.update_layout(
        title=f"Damage Multiplier vs. Uniform in {yrs[-1]} (Red = More Damage, Green = Less Damage)",
        xaxis_title="Region", yaxis_title="Damage Multiplier",
        margin={"l": 60, "r": 30, "t": 50, "b": 70},
    )

    gini_min = min(gini) if gini else 0.0
    gini_max = max(gini) if gini else 1.0
    gini_pad = (gini_max - gini_min) * 0.08 or 0.02
    fig3 = base_fig(height=380)
    fig3.add_trace(go.Scatter(
        x=yrs, y=gini, name="Gini Index",
        line={"color": "#e9c46a", "width": 2},
        fill="tozeroy", fillcolor="rgba(233,196,106,0.07)",
        hovertemplate="Gini Index: %{y:.3f}<extra></extra>",
    ))
    fig3.update_layout(
        title="Regional Consumption Inequality",
        xaxis_title="Year", yaxis_title="Gini Index (0 = equal, 1 = maximal)",
        yaxis={"range": [max(0.0, gini_min - gini_pad), gini_max + gini_pad]},
    )

    if dmg_frac and regions_to_show:
        last_t = len(yrs) - 1
        max_ri  = max(regions_to_show, key=lambda r: dmg_frac[r][last_t])
        min_ri  = min(regions_to_show, key=lambda r: dmg_frac[r][last_t])
        max_dmg = dmg_frac[max_ri][last_t] * 100
        min_dmg = dmg_frac[min_ri][last_t] * 100
    else:
        max_ri = min_ri = 0; max_dmg = min_dmg = 0.0

    cfg = {"displayModeBar": False}
    children = [
        _ctx(
            "Damage fractions show climate losses as a percentage of regional gross output — "
            "small on average but highly unequal across regions. Tropical, low-elevation, and "
            "lower-income regions typically face disproportionately large burdens relative to "
            "their economic share. The damage multiplier chart reveals how each region's burden "
            "compares to the global uniform average under the chosen welfare function — red bars "
            "signal regions bearing above-average relative damages. The Gini index tracks whether "
            "climate change and abatement policy collectively narrow or widen consumption "
            "inequality over time: a rising Gini means growth and damages are accruing "
            "unequally. These equity dimensions are central to climate justice debates and "
            "international climate finance negotiations."
        ),
        dcc.Graph(figure=fig1, config=cfg, responsive=True, style={"height": "600px"}),
        dcc.Graph(figure=fig2, config=cfg, responsive=True, style={"height": "380px"}),
        dcc.Graph(figure=fig3, config=cfg, responsive=True, style={"height": "380px"}),
        html.Div(
            "Note: The Gini index changes little across welfare functions because the welfare "
            "function in this model is a measurement framework — it changes how outcomes are "
            "scored, not how the economy operates. The only feedback into the economy is a "
            "small redistribution of climate damage burdens between regions, which is dwarfed "
            "by the large baseline consumption inequality between regions set by the SSP. To "
            "meaningfully shift the Gini, the model would need inter-regional transfers, "
            "differentiated abatement burden-sharing, or welfare-weighted savings rates.",
            style={"color": "#6a8aa8", "fontSize": "12px", "fontStyle": "italic",
                   "lineHeight": "1.55", "marginTop": "4px", "marginBottom": "12px"},
        ),
        summary_box([
            ("Highest Regional Damage", f"{max_dmg:.2f}% of GDP", f"({REGIONS[max_ri]})"),
            ("Lowest Regional Damage",  f"{min_dmg:.2f}% of GDP", f"({REGIONS[min_ri]})"),
        ]),
    ]
    return html.Div(children)


def tab_about():
    cards = [
        html.Div(style={
            "border": "1px solid #243448",
            "padding": "14px 18px", "marginBottom": "10px",
        }, children=[
            html.Div(title, style={"color": "#c8dff0", "fontWeight": "700",
                                   "fontSize": "14px", "marginBottom": "6px"}),
            dcc.Markdown(body, className="about-body"),
        ])
        for title, body in ABOUT_TEXT
    ]
    return html.Div(
        style={"maxWidth": "1100px", "margin": "0 auto", "paddingTop": "8px"},
        children=[
            html.Div("About This Model",
                     style={"color": "#b0c8e0", "fontSize": "16px",
                            "fontWeight": "700", "marginBottom": "16px"}),
            *cards,
        ],
    )
