from dash import html, dcc
import dash_bootstrap_components as dbc
from .companies_jobs import get_company_component, register_company_callbacks, all_companies, default_companies

def get_companies_layout():
    return html.Div([
        dcc.Loading(
            id="companies-loading",
            type="circle",
            color="#00BFFF",
            fullscreen=False,
            children=html.Div([
                dbc.Row([
                    get_company_component(),
                ]),
                html.Br()
            ])
        )
    ])

def register_companies_callbacks(app):
    register_company_callbacks(app)
