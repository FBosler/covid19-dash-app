import dash
import os
import plotly.express as px
import pandas as pd
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
import json
from urllib.request import urlopen
from dash.dependencies import Input, Output
from apscheduler.schedulers.background import BackgroundScheduler


def fetch_counties():
    URL = "https://raw.githubusercontent.com/isellsoap/deutschlandGeoJSON/master/4_kreise/4_niedrig.geojson"
    with urlopen(URL) as response:
        counties = json.load(response)
    return counties


def create_fig(df, counties):
    fig = px.choropleth(
        data_frame=df,
        geojson=counties,
        color="log(infected+1)",
        color_continuous_scale='oranges',
        hover_name='infected',
        hover_data=['Landkreis'],
        locations="Landkreis",
        featureidkey="properties.NAME_3",
        projection="mercator",
        #animation_frame='date'
    )

    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        height=1000,
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )

    fig.add_scattergeo(
        geojson=counties,
        locations=df['Landkreis'],
        text=df['Landkreis'],
        textfont=dict(
            family="sans serif",
            size=12,
            color="Black"
        ),
        featureidkey="properties.NAME_3",
        mode='text',
    )

    return fig


def load_data():
    global data
    _ = pd.read_csv(os.path.join(os.path.dirname(__file__), 'data.csv'))
    available_dates = _[_['infected'] != 0].date.unique()
    data = _[_.date == "17-03"]
    return data


data = load_data()

## dropdown config
BUNDESLAENDER = [{'label':'All', 'value':'All'}]
BUNDESLAENDER.extend([{'label': land, 'value': land} for land in data.Bundesland.unique()])


cron = BackgroundScheduler()
cron.add_job(func=load_data, trigger="interval", seconds=10)
cron.start()

counties = fetch_counties()

fig = create_fig(df=data, counties=counties)

external_stylesheets = [dbc.themes.BOOTSTRAP]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)


app.layout = html.Div([
        dbc.Container([
            html.H1(children='Visualization of reported Covid-19 cases in Germany by Districts'),
            dcc.Link(
                'Date taken from the RKI page',
                href='https://www.rki.de/DE/Content/InfAZ/N/Neuartiges_Coronavirus/Situationsberichte/Gesamt.html'
            ),
            html.Br(),

            dbc.Row([
                    # Select City
                    dbc.Label(
                        "Bundesland",
                        html_for="select-bundesland",
                        id='select-bundesland-label',
                        width=2
                    ),
                    dbc.Tooltip(
                        "Select the county to zoom in",
                        target="select-bundesland-label",
                    ),
                    dbc.Col([
                        dcc.Dropdown(
                            id='select-bundesland',
                            options=BUNDESLAENDER,
                            value='All'
                        ),
                    ], width=10)
            ]),

            dbc.Row([
                dbc.Col([
                    dcc.Graph(
                        id='infected-graph',
                        figure=fig
                    ),

                    dcc.Interval(
                        id='interval-component',
                        interval=1 * 1000 * 30,
                        n_intervals=0
                    )
                ], md=12)
            ])
    ], fluid=True)
])

server = app.server

current_interval = 0

@app.callback(
    Output('infected-graph', 'figure'),
[
    Input('select-bundesland', 'value'),
    Input('interval-component', 'n_intervals'),
])
def update_figure(bundesland, n):
    global current_interval
    if current_interval != n:
        current_interval = n
        load_data()

    if bundesland == 'All':
        filtered_df = data
    else:
        filtered_df = data[data.Bundesland == bundesland]

    return create_fig(filtered_df, counties)

if __name__ == '__main__':
    app.run_server()