import dash
import dcc as dcc
from dash import dcc, html
from flask import Flask
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objs as go
import plotly.express as px
from dash.dependencies import Input, Output
from jupyter_dash import JupyterDash

# Load data from the CSV file
df = pd.read_csv('ob_report_2023.csv')

# Specify the date format
date_format = '%m/%d/%y'

# Convert date columns to datetime objects
df['Date Outbreak Began'] = pd.to_datetime(df['Date Outbreak Began'], format=date_format)
df['Date Declared Over'] = pd.to_datetime(df['Date Declared Over'], format=date_format)

# app = dash.Dash(__name__)
app = JupyterDash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Define the app layout

app.layout = dash.html.Div(
    [
        html.H1("Carehome Outbreaks Dashboard",
                style={'textAlign': 'left', 'padding-left': '20px', 'padding-top': '20px'}),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Row(
                        [
                            dash.html.Label("Facility"),
                            dcc.Dropdown(
                                id='outbreak-setting-dropdown',
                                options=[{'label': str(setting), 'value': str(setting)} for setting in
                                         df['Outbreak Setting'].unique()],
                                multi=True,
                                placeholder="Select Outbreak Setting"
                            ),
                        ],
                        justify="center", style={'background-color': '#D3D3D3', 'height': '100px',
                                                 'margin': '10px', 'padding': '20px', 'font-size': '18px',
                                                },
                    ),
                ),
                dbc.Col(
                    dbc.Row(
                        [
                            dash.html.Label("Cause of Outbreak"),
                            dcc.Dropdown(
                                id='outbreak-cause-dropdown',
                                options=[{'label': str(setting), 'value': str(setting)} for setting in
                                         df['Causative Agent-1'].unique()],
                                multi=True,
                                placeholder="Cause of Outbreak"
                            ),
                        ],
                        justify="center", style={'background-color': '#D3D3D3', 'height': '100px',
                                                 'margin': '10px', 'padding': '20px', 'font-size': '18px',
                                                 },
                    ),
                ),
                dbc.Col(
                    dbc.Row(
                        [
                            dash.html.Label("Date"),
                            dcc.DatePickerRange(
                                id='date-range-picker',
                                min_date_allowed=df['Date Outbreak Began'].min(),
                                max_date_allowed=df['Date Declared Over'].max(),
                                initial_visible_month=df['Date Outbreak Began'].min(),
                                start_date=df['Date Outbreak Began'].min(),
                                end_date=df['Date Declared Over'].max(),
                                style={'width': '100%'},  # Adjust the width as desired
                                # start_date_placeholder_text="Start Period",
                                # end_date_placeholder_text="End Period"

                            ),
                        ],
                        justify="center", style={'background-color': '#D3D3D3', 'height': '100px',
                                                 'margin': '10px', 'padding': '10px', 'font-size': '18px',
                                                 },
                    )
                ),
            ],
            justify="center",
        ),
        # Line chart
        html.Div(dcc.Graph(id='line-chart'), style={'width': '50%', 'display': 'inline-block'}),

        # Bar chart
        html.Div(dcc.Graph(id='column-chart'), style={'width': '50%', 'display': 'inline-block'}),

        # Pie chart
        html.Div(dcc.Graph(id='pie-chart'), style={'width': '50%', 'display': 'inline-block'}),
    ],
    style={"font-family": "Arial", "font-size": "0.9em", "text-align": "center"},
)


# Define callback functions to update graphs
@app.callback(
    Output('line-chart', 'figure'),
    Output('column-chart', 'figure'),
    Output('pie-chart', 'figure'),
    Input('outbreak-setting-dropdown', 'value'),
    Input('date-range-picker', 'start_date'),
    Input('date-range-picker', 'end_date')
)
def update_graphs(selected_settings, start_date, end_date):
    filtered_df = df

    # Filter by selected Outbreak Settings
    if selected_settings:
        filtered_df = filtered_df[filtered_df['Outbreak Setting'].isin(selected_settings)]

    # Update Line Chart (line chart)
    line_fig = px.line(filtered_df, x=filtered_df['Date Outbreak Began'], y=filtered_df['Active'],
                      title='Active Outbreaks Over Time')
    
    line_fig.update_layout(yaxis=dict(autorange="reversed"))


    # Update Column Chart (replacing bar chart)
    column_fig = go.Figure(data=[
        go.Bar(x=filtered_df['Institution Name'].str[:15], y=filtered_df['Active'])
    ])
    column_fig.update_layout(title_text='Active Status Column Chart', xaxis_title='Institution Name',
                             yaxis_title='Active')

    # Update Pie Chart
    pie_fig = px.pie(filtered_df, names='Type of Outbreak', title='Type of Outbreak Pie Chart')

    # Adjust the size of the Pie Chart
    pie_fig.update_layout(height=700, width=1000)  # You can adjust the height and width as needed

    return line_fig, column_fig, pie_fig


if __name__ == "__main__":
    app.run_server(mode="inline")
