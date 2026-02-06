import dash
from dash import html, dcc, Output, Input
import dash_bootstrap_components as dbc

# Imports
from companies.companies_jobs import get_company_component
from jobs.main import get_jobs_layout, register_jobs_callbacks, all_titles
from industries.main import get_industries_layout, register_industries_callbacks, all_industries, default_industries
from companies.main import get_companies_layout, register_company_callbacks, all_companies, default_companies
from listings.main import get_listings_layout, register_listings
from constants.default import defaultJobTitle

# App setup
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = "JobBuddy"

# Sidebar
sidebar = dbc.Col(
    [
        html.H4("Filters", className="text-white mb-3"),

        html.Label("Select Job Titles", className="text-white"),
        dcc.Dropdown(
            id='title-selector',
            options=[{"label": title, "value": title} for title in all_titles],
            value=defaultJobTitle,
            multi=True,
            persistence=True,
            persistence_type='memory',
            className="mb-4",
            style={"backgroundColor": "#1c1c1c"}
        ),

        html.Div(id="dynamic-dropdown-container")
    ],
    width=3,
    style={"backgroundColor": "#343a40", "padding": "20px", "minHeight": "100vh", "overflow": "hidden"}
)

# Tabs
tabs_component = dbc.Row([
    dbc.Col(
        dbc.Tabs([
            dbc.Tab(label="Industries", tab_id="industries"),
            dbc.Tab(label="Companies", tab_id="companies"),
            dbc.Tab(label="Jobs", tab_id="jobs"),
            dbc.Tab(label="Listings", tab_id="listings"),
        ], id="tabs", active_tab="industries", className="mb-4"),
        width=12
    )
], style={"position": "sticky", "top": 0, "zIndex": 1000, "backgroundColor": "#1e1e1e"})

# Layout
app.layout = dbc.Container([
    dbc.Row([
        sidebar,
        dbc.Col([
            tabs_component,
            html.Div(id="tab-content")
        ], width=9, style={"maxHeight": "100vh", "overflowY": "auto"})
    ])
], fluid=True, style={"backgroundColor": "#1e1e1e", "minHeight": "100vh"})

# Tab routing
@app.callback(Output("tab-content", "children"), Input("tabs", "active_tab"))
def render_tab(tab):
    if tab == "industries":
        return html.Div([
            dbc.Row([get_industries_layout()]),
            html.Br(),
        ])
    elif tab == "companies":
       return html.Div([
            dbc.Row([get_companies_layout()]),
            html.Br(),
        ])
    elif tab == "jobs":
        return get_jobs_layout()
    elif tab == "listings":
        return html.Div([
            dbc.Row([get_listings_layout()]),
            html.Br(),
        ])

# Sidebar dynamic filter update
@app.callback(
    Output("dynamic-dropdown-container", "children"),
    Input("tabs", "active_tab")
)
def toggle_dropdown(tab):
    if tab == "companies" or tab == "listings":
        return [
            html.Label("Select Companies", className="text-white"),
            dcc.Dropdown(
                id='company-dropdown',
                options=[{"label": c, "value": c} for c in all_companies],
                value=default_companies,
                multi=True,
                persistence=True,
                persistence_type='memory',
                className="mb-4",
                style={"backgroundColor": "#1c1c1c"}
            )
        ]
    elif tab == "industries" or tab == "listings":
        return [
            html.Label("Select Industries", className="text-white"),
            dcc.Dropdown(
                id='industry-dropdown',
                options=[{"label": ind, "value": ind} for ind in all_industries],
                value=default_industries,
                multi=True,
                persistence=True,
                persistence_type='memory',
                className="mb-4",
                style={"backgroundColor": "#1c1c1c"}
            )
        ]
    return []

# Register callbacks
register_jobs_callbacks(app)
register_industries_callbacks(app)
register_company_callbacks(app)
register_listings(app)

if __name__ == '__main__':
    app.run(debug=True, port=8051)
