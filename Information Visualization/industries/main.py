from dash import html, dcc
import dash_bootstrap_components as dbc
from .industries_jobs import get_industry_component, register_industry_callbacks,all_industries,default_industries


def get_industries_layout():
    return html.Div([
        dcc.Loading(
            id="industries-loading",
            type="circle",
            color="#00BFFF",
            fullscreen=False,
            children=html.Div([
                dbc.Row([
                    get_industry_component(),
                ]),
                html.Br()
            ])
        )
    ])

def register_industries_callbacks(app):
    register_industry_callbacks(app)
