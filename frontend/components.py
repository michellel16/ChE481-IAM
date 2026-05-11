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
            html.Span(text, style={"color": "#a4bdd6", "fontSize": "12px", "fontWeight": "700",
                                   "textTransform": "uppercase", "letterSpacing": "1px"}),
            dcc.Input(id=input_id, style={**INPUT_STYLE, "width": "60px"}, **input_kwargs),
        ],
    )

def section_head(text, color=ACCENT):
    return html.Div(text, style={
        "color": color, "fontSize": "14px", "fontWeight": "800",
        "textTransform": "uppercase", "letterSpacing": "1.3px",
        "marginTop": "6px", "marginBottom": "4px",
    })


def divider():
    return html.Hr(style={"border": "none", "borderTop": "1px solid #607898",
                           "margin": "18px 0 8px"})

def stat_card(title, value, sub, color):
    return html.Div(className="stat-card", style={"borderLeft": f"3px solid {color}"}, children=[
        html.Div(title, className="stat-title"),
        html.Div(value, className="stat-value"),
        html.Div(sub,   className="stat-sub"),
    ])

def stats_row(cards):
    return html.Div(cards, className="stats-row")

def summary_box(items):
    """items: list of (title, value, sub) tuples."""
    rows = []
    for title, value, sub in items:
        rows.append(html.Div(className="summary-row", children=[
            html.Span(f"{title}: ", className="summary-label"),
            html.Span(value,        className="summary-value"),
            html.Span(f"  {sub}",   className="summary-sub") if sub else None,
        ]))
    return html.Div(rows, className="summary-box")


def base_fig(height=600):
    fig = go.Figure()
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG, plot_bgcolor=PLOT_BG,
        font={"color": "#b0c8e0", "family": "Cambria Math, Cambria, serif", "size": 13},
        title_font_size=18,
        legend={"bgcolor": "#161d2e", "bordercolor": "#243448", "borderwidth": 1,
                "x": 0.99, "y": 0.99, "xanchor": "right", "yanchor": "top"},
        margin={"l": 80, "r": 50, "t": 65, "b": 65},
        height=height, hovermode="x unified",
    )
    fig.update_xaxes(showline=True, linecolor="#607898", linewidth=1, mirror=True,
                     ticks="outside", ticklen=16)
    fig.update_yaxes(showline=True, linecolor="#607898", linewidth=1, mirror=True,
                     ticks="outside", ticklen=16)
    return fig