import pandas as pd
import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table, Input, Output
from shared.utils import job_titles

# Load and clean data
df_jobs = pd.read_csv("data/cleaned.csv")
df_jobs = job_titles(df_jobs)

# Convert timestamp
df_jobs['original_listed_time'] = pd.to_datetime(df_jobs['original_listed_time'].astype(float), unit='ms', utc=True)
df_jobs['listed_date'] = df_jobs['original_listed_time'].dt.strftime('%b %d, %Y')

# Merge industry data
df_industries = pd.read_csv('data/job_industries.csv')
ind = pd.read_csv('data/industries.csv')
industry_mapping = dict(zip(ind['industry_id'], ind['industry_name']))
df_industries['industry_name'] = df_industries['industry_id'].map(industry_mapping)

# Merge job & industry
df_merged = pd.merge(df_jobs, df_industries[['job_id', 'industry_name']], on='job_id', how='left')

# Layout component
def get_listings_component():
    return dbc.Col(
        dash_table.DataTable(
            id='job-listings-table',
            columns=[
                {"name": "Job Title", "id": "title"},
                {"name": "Company", "id": "company_name"},
                {"name": "Industry", "id": "industry_name"},
                {"name": "Location", "id": "location"},
                {"name": "Work Type", "id": "formatted_work_type"},
                {"name": "Experience", "id": "formatted_experience_level"},
                {"name": "Salary", "id": "salary_range"},
                {"name": "Posted On", "id": "listed_date"}
            ],
            data=[],
            style_table={'overflowX': 'auto', 'backgroundColor': '#1e1e1e'},
            style_header={
                'backgroundColor': '#343a40',
                'color': 'white',
                'fontWeight': 'bold'
            },
            style_cell={
                'backgroundColor': '#1e1e1e',
                'color': 'white',
                'textAlign': 'left',
                'font_family': 'Arial',
                'font_size': '14px',
                'padding': '8px'
            },
            page_size=15,
            sort_action="native",
            filter_action="native",
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#2b2b2b'
                }
            ]
        ),
        width=12
    )

# Register callback
def register_listings_callbacks(app):
    @app.callback(
        Output('job-listings-table', 'data'),
        [
            Input('title-selector', 'value'),
            Input('industry-dropdown', 'value'),
            Input('company-dropdown', 'value')
        ]
    )
    def update_table(titles, industries, companies):
        filtered = df_merged.copy()

        if titles:
            filtered = filtered[filtered['title'].isin(titles)]
        if industries:
            filtered = filtered[filtered['industry_name'].isin(industries)]
        if companies:
            filtered = filtered[filtered['company_name'].isin(companies)]

        # Create salary range column
        filtered['salary_range'] = filtered.apply(
            lambda row: f"${row['min_salary']} - ${row['max_salary']}" if pd.notnull(row['min_salary']) and pd.notnull(row['max_salary']) else "N/A",
            axis=1
        )

        return filtered[[
            'title', 'company_name', 'industry_name', 'location',
            'formatted_work_type', 'formatted_experience_level',
            'salary_range', 'listed_date'
        ]].to_dict('records')

# Export
__all__ = ['get_listings_component', 'register_listings_callbacks']
