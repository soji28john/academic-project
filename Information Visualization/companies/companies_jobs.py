import pandas as pd
import plotly.express as px
import dash_bootstrap_components as dbc
from dash import dcc, Input, Output
from shared.utils import job_titles

# Load data
df_jobs = pd.read_csv('data/cleaned.csv')
df_jobs = job_titles(df_jobs)

# Get all company names
company_counts = df_jobs['company_name'].value_counts().reset_index()
company_counts.columns = ['Company', 'Number of Jobs']
company_counts = company_counts.sort_values('Number of Jobs', ascending=False)
all_companies = company_counts['Company'].dropna().tolist()

# Default company filter based on default job title
default_title = "Marketing Coordinator"
default_jobs = df_jobs[df_jobs['title'] == default_title]
default_companies = (
    default_jobs['company_name']
    .value_counts()
    .dropna()
    .head(10)
    .index
    .tolist()
)

def get_company_component():
    return dbc.Col(
        dcc.Graph(id='company-bar-chart'),
        width=12
    )

def register_company_callbacks(app):
    @app.callback(
        Output('company-bar-chart', 'figure'),
        [Input('company-dropdown', 'value'),
         Input('title-selector', 'value')],
        prevent_initial_call=True
    )
    def update_graph(selected_companies, selected_titles):
        if not selected_titles:
            return px.bar(
                title="No job titles selected",
                template='plotly_dark'
            ).update_layout(
                height=600,
                margin=dict(b=100),
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                annotations=[dict(
                    text="Please select at least one job title",
                    xref="paper", yref="paper",
                    showarrow=False,
                    font=dict(size=16, color="white")
                )]
            )

        if not selected_companies:
            return px.bar(
                title="No companies selected",
                template='plotly_dark'
            ).update_layout(
                height=600,
                margin=dict(b=100),
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                annotations=[dict(
                    text="Please select at least one company",
                    xref="paper", yref="paper",
                    showarrow=False,
                    font=dict(size=16, color="white")
                )]
            )

        stacked_data = []

        for company in selected_companies:
            jobs_in_company = df_jobs[df_jobs['company_name'] == company]

            for title in selected_titles:
                count = jobs_in_company[jobs_in_company['title'] == title].shape[0]
                if count > 0:
                    stacked_data.append({
                        'Company': company,
                        'Job Title': title,
                        'Number of Jobs': count
                    })

        stacked_df = pd.DataFrame(stacked_data)

        if stacked_df.empty:
            fig = px.bar(
                pd.DataFrame({'Company': selected_companies, 'Number of Jobs': [0] * len(selected_companies)}),
                x='Company',
                y='Number of Jobs',
                title='No matching jobs found for the selected criteria',
                template='plotly_dark'
            )
        else:
            fig = px.bar(
                stacked_df,
                x='Company',
                y='Number of Jobs',
                color='Job Title',
                title='No: of Jobs by Company and Title',
                template='plotly_dark',
                barmode='group'
            )

            fig.update_traces(
                hovertemplate='<b>%{data.name}</b><br>Jobs: %{y}<extra></extra>',
                hoverlabel=dict(
                    bgcolor="black",
                    font_size=14,
                    font_family="Arial",
                    font_color="white"
                ),
                selected=dict(marker=dict(opacity=1)),
                unselected=dict(marker=dict(opacity=0.1))
            )

        fig.update_layout(
            xaxis_tickangle=-45,
            height=600,
            margin=dict(b=100),
            hovermode='closest',
            clickmode='event+select',
            yaxis=dict(
                tickmode='linear',
                dtick=1,
                tickformat='d'
            ),
            legend_title_text='Job Titles'
        )

        return fig

    @app.callback(
        Output('company-dropdown', 'options'),
        Output('company-dropdown', 'value'),
        Input('title-selector', 'value')
    )
    def update_company_dropdown(selected_titles):
        if not selected_titles:
            return [], []

        filtered = df_jobs[df_jobs['title'].isin(selected_titles)]
        options = sorted(filtered['company_name'].dropna().unique().tolist())
        top_companies = (
            filtered['company_name']
            .value_counts()
            .dropna()
            .head(10)
            .index
            .tolist()
        )

        return [{'label': c, 'value': c} for c in options], top_companies

# Export shared data
__all__ = ['get_company_component', 'register_company_callbacks', 'all_companies', 'default_companies']
