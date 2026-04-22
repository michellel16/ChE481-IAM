"""
IAM_BACKEND_URL, Base URL of the backend (default: http://localhost:5001)
IAM_FRONTEND_PORT, Port for Dash app (default: 8050)
"""

import os
import dash

from layout import build_layout
import callbacks  # noqa: F401 — registers all Dash callbacks

app = dash.Dash(__name__, title="IAM Explorer",
                assets_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets"),
                prevent_initial_callbacks="initial_duplicate")

app.layout = build_layout()

if __name__ == "__main__":
    port = int(os.environ.get("IAM_FRONTEND_PORT", 8050))
    app.run(debug=False, port=port)
