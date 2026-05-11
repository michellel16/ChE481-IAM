import os
import dash

from layout import build_layout
import callbacks  # noqa: F401 — registers all Dash callbacks

app = dash.Dash(__name__, title="IAM dying",
                assets_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets"),
                prevent_initial_callbacks="initial_duplicate")

app.index_string = '''<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        <link rel="icon" href="data:,">
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>'''

app.layout = build_layout()
server = app.server  # expose Flask server for gunicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", os.environ.get("IAM_FRONTEND_PORT", 8050)))
    app.run(host="0.0.0.0", debug=False, port=port)
