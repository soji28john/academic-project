import pandas as pd
import plotly.express as px
import dash_bootstrap_components as dbc
from dash import dcc, Input, Output
from shared.utils import job_titles

# Load data
df_industries = pd.read_csv('data/job_industries.csv')
ind = pd.read_csv('data/industries.csv')
df_jobs = pd.read_csv('data/cleaned.csv')

# Clean job titles as done in radar.py
df_jobs = job_titles(df_jobs)

# Map industry IDs to names
industry_mapping = dict(zip(ind['industry_id'], ind['industry_name']))
df_industries['industry_name'] = df_industries['industry_id'].map(industry_mapping)

# Join tables to connect industries with job titles
industry_jobs = pd.merge(df_industries, df_jobs, on='job_id', how='inner')

# Get all industry names
industry_counts = df_industries['industry_name'].value_counts().reset_index()
industry_counts.columns = ['Industry', 'Number of Jobs']
industry_counts = industry_counts.sort_values('Number of Jobs', ascending=False)
all_industries = industry_counts['Industry'].tolist()

# Compute default industries based on the default job title
default_title = "Marketing Coordinator"
default_job_ids = df_jobs[df_jobs['title'] == default_title]['job_id'].unique()
default_industry_jobs = df_industries[df_industries['job_id'].isin(default_job_ids)]
industry_counts_default = (
    default_industry_jobs['industry_name']
    .value_counts()
    .dropna()
    .head(10)
    .index
    .tolist()
)
default_industries = industry_counts_default

def get_industry_component():
    return dbc.Col(
        dcc.Graph(id='industry-bar-chart'),
        width=12
    )

def register_industry_callbacks(app):
    @app.callback(
        Output('industry-bar-chart', 'figure'),
        [Input('industry-dropdown', 'value'),
         Input('title-selector', 'value')],
        prevent_initial_call=True
    )
    def update_graph(selected_industries, selected_titles):
        if not selected_titles or len(selected_titles) == 0:
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

        if not selected_industries or len(selected_industries) == 0:
            return px.bar(
                title="No industries selected",
                template='plotly_dark'
            ).update_layout(
                height=600,
                margin=dict(b=100),
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                annotations=[dict(
                    text="Please select at least one industry",
                    xref="paper", yref="paper",
                    showarrow=False,
                    font=dict(size=16, color="white")
                )]
            )

        titles_to_show = selected_titles if selected_titles and len(selected_titles) > 0 else df_jobs['title'].unique()

        stacked_data = []

        for industry in selected_industries:
            industry_job_ids = df_industries[df_industries['industry_name'] == industry]['job_id'].unique()
            industry_jobs = df_jobs[df_jobs['job_id'].isin(industry_job_ids)]

            for title in titles_to_show:
                count = industry_jobs[industry_jobs['title'] == title].shape[0]
                if count > 0:
                    stacked_data.append({
                        'Industry': industry,
                        'Job Title': title,
                        'Number of Jobs': count
                    })

        stacked_df = pd.DataFrame(stacked_data)

        if stacked_df.empty:
            fig = px.bar(
                pd.DataFrame({'Industry': selected_industries, 'Number of Jobs': [0] * len(selected_industries)}),
                x='Industry',
                y='Number of Jobs',
                title='No matching jobs found for the selected criteria',
                template='plotly_dark'
            )
        else:
            fig = px.bar(
                stacked_df,
                x='Industry',
                y='Number of Jobs',
                color='Job Title',
                title='No: of Jobs by Industry and Title',
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
                )
            )

        fig.update_layout(
            xaxis_tickangle=-45,
            height=600,
            margin=dict(b=100),
            hovermode='closest',
            yaxis=dict(
                tickmode='linear',
                dtick=1,
                tickformat='d'
            ),
            legend_title_text='Job Titles'
        )

        return fig

    @app.callback(
        Output('industry-dropdown', 'options'),
        Output('industry-dropdown', 'value'),
        Input('title-selector', 'value')
    )
    def update_industry_dropdown(selected_titles):
        if not selected_titles:
            return [], []

        filtered_jobs = df_jobs[df_jobs['title'].isin(selected_titles)]
        merged = pd.merge(df_industries, filtered_jobs, on='job_id', how='inner')

        options = sorted(merged['industry_name'].dropna().unique().tolist())
        top_industries = (
            merged['industry_name']
            .value_counts()
            .dropna()
            .head(10)
            .index
            .tolist()
        )

        return [{'label': ind, 'value': ind} for ind in options], top_industries

# Export shared data
__all__ = ['get_industry_component', 'register_industry_callbacks', 'all_industries', 'default_industries']
