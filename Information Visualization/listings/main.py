from dash import html, dcc
import dash_bootstrap_components as dbc
from .job_listings import get_listings_component, register_listings_callbacks

def get_listings_layout():
    return dbc.Container([
        dcc.Loading(
            id="listings-loading",
            type="circle",
            color="#00BFFF",
            fullscreen=False,
            children=dbc.Row([
                get_listings_component()
            ])
        )
    ], fluid=True)

def register_listings(app):
    register_listings_callbacks(app)
