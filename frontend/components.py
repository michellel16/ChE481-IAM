from dash import dcc, html
import plotly.graph_objects as go

from constants import ACCENT, BG, PLOT_BG, INPUT_STYLE

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
        legend={"bgcolor": "#161d2e", "bordercolor": "#243448", "borderwidth": 1,
                "x": 0.99, "y": 0.99, "xanchor": "right", "yanchor": "top"},
        margin={"l": 60, "r": 30, "t": 50, "b": 50},
        height=height, hovermode="x unified",
    )
    return fig