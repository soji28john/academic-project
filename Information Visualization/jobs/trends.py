import pandas as pd
import plotly.express as px
from dash import dcc, html
import dash_bootstrap_components as dbc

# Load and preprocess the data
df = pd.read_csv("data/cleaned.csv")
df['listed_datetime'] = pd.to_datetime(df['original_listed_time'], unit='ms')
df['YearMonth'] = df['listed_datetime'].dt.to_period('M').astype(str)

monthly_counts = df.groupby('YearMonth').size().reset_index(name='Job Postings')

# Layout component for line chart
def get_line_chart():
    return dbc.Col([
        dcc.Graph(
            figure=px.line(
                monthly_counts,
                x='YearMonth',
                y='Job Postings',
                title='Job Postings Trends by Month',
                markers=True
            ).update_layout(
                xaxis_title='Month',
                yaxis_title='Number of Job Postings',
                title_x=0.5,
                template='plotly_dark',
                height=600
            )
        )
    ], width=6)
