import pandas as pd
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from shared.utils import job_titles
from dash import dcc
from dash.dependencies import Input, Output

# Load and clean the data
df = pd.read_csv('data/cleaned.csv')

df_jobs = job_titles(df)

df['original_listed_time'] = pd.to_datetime(df['original_listed_time'].astype(float), unit='ms', utc=True)

# Calculate day of week
if 'Days' in df.columns:
    df['day_of_week'] = df['Days'].astype(str).str.strip()
else:
    df['day_of_week'] = df['original_listed_time'].dt.day_name()

day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
all_titles = sorted(df['title'].dropna().unique())

# Layout component for radar chart
def get_radar_component():
    return dbc.Col([
        dcc.Graph(id='radar-chart')
    ], width=6)

# Callback registration
def register_radar_callbacks(app):
    @app.callback(
        Output('radar-chart', 'figure'),
        Input('title-selector', 'value')
    )
    def update_radar_chart(selected_titles):
        if not selected_titles:
            return go.Figure().update_layout(
                title="No job titles selected",
                template='plotly_dark',
                height=400,
                polar=dict(radialaxis=dict(visible=False)),
                annotations=[dict(
                    text="Please select at least one job title",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5,
                    showarrow=False,
                    font=dict(size=16, color="white"),
                    align="center"
                )]
            )

        fig = go.Figure()
        has_data = False

        for title in selected_titles:
            df_title = df[df['title'] == title]
            daily_counts = df_title.groupby('day_of_week').size().reindex(day_order, fill_value=0)

            if daily_counts.sum() == 0:
                continue

            has_data = True
            values = daily_counts.tolist()
            categories = daily_counts.index.tolist()

            values.append(values[0])
            categories.append(categories[0])

            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories,
                name=title,
                fill='toself',
                hoverinfo='text',
                hovertemplate=f'<b>{title}</b><br><b>%{{theta}}</b><br>%{{r}} jobs<extra></extra>'
            ))

        if has_data:
            max_value = max([
                df[df['title'] == t].groupby('day_of_week').size().max()
                for t in selected_titles if not df[df['title'] == t].empty
            ] + [1])

            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, max_value],
                        tickmode='linear',
                        dtick=1,
                        tickformat='d'
                    )
                ),
                showlegend=True,
                title="Daily Job Posting Frequency (UTC)",
                template='plotly_dark',
                height=700,
                hoverlabel=dict(
                    bgcolor="black",
                    font_size=14,
                    font_family="Arial",
                    font_color="white"
                )
            )
        else:
            fig.update_layout(
                title="No Data Available for Selected Job Titles",
                template='plotly_dark',
                height=700
            )

        return fig
