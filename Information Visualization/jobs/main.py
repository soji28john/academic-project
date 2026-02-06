from dash import dcc, html
import dash_bootstrap_components as dbc
from .radar import get_radar_component, register_radar_callbacks,all_titles
from .trends import get_line_chart

def get_jobs_layout():
    return dbc.Container([
        dcc.Loading(
            id="jobs-loading",
            type="circle",
            children=dbc.Row([
                get_radar_component(),
                get_line_chart()
            ], className="mt-4"),
        )
    ], fluid=True)

def register_jobs_callbacks(app):
    register_radar_callbacks(app)
    # No additional callbacks needed for trends at this point
