import pandas as pd
import plotly.express as px
import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objs as go

# import api_requests.py module who contains data extraction functions
import api_requests as api

# calls data extraction functions
# they will create csv files with extracted and filtered data
# functions return generated csv file path
csv_file_path = api.firstapi_data_extraction()
df0 = pd.read_csv(csv_file_path)
csv_file_path = api.secondapi_data_extraction()
df = pd.read_csv(csv_file_path)

# merge section
df = df[['location', 'country', 'city', 'latitude', 'longitude', 'pm25', 'pm10', 'no2', 'o3', 'last_updated', 'size']]
df0 = df0[['location', 'latitude', 'longitude', 'aqi', 'last_updated', 'size']]
merged_df = pd.concat([df, df0], ignore_index=True)
merged_df = merged_df[['location', 'country', 'city', 'latitude', 'longitude', 
                       'pm25', 'pm10', 'no2', 'o3', 'aqi', 'last_updated', 'size']]

# convert aqi type from int to float (must be float for continuos scale rapresentation)
merged_df['aqi'] = merged_df['aqi'].astype(float)

# copy the value from 'location' to 'city' for each row if 'city' is null
# world_air_quality_data has no values for city
merged_df['city'] = merged_df.apply(
    lambda row: row['location'] if pd.isna(row['city']) or row['city'] == '' else row['city'], 
    axis=1
)

# save merged df into CSV
merged_df.to_csv("merged_data.csv", index=False)


# initialize the Dash app
app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

# create the layout of the app
app.layout = html.Div([
    # navbar with only the black top banner and the title
    dbc.NavbarSimple(
        brand="World Air Quality Map",
        brand_href="#",
        color="Black",
        dark=True,
    ),
    # map graph
    dcc.Graph(id='air-quality-map', style={"margin-bottom": "0px"}),
    html.Div(
        dbc.Container(
            # map selectors buttons
            dbc.ButtonGroup([
                dbc.Button("AQI", id="btn-aqi", n_clicks=0, color="primary", outline=True, style={'borderColor': 'white','borderRadius': '0', 'color': 'white'}),
                dbc.Button("PM 2.5", id="btn-pm25", n_clicks=0, color="primary", outline=True, style={'borderColor': 'white','borderRadius': '0', 'color': 'white'}),
                dbc.Button("PM 10", id="btn-pm10", n_clicks=0, color="primary", outline=True, style={'borderColor': 'white','borderRadius': '0', 'color': 'white'}),
                dbc.Button("NO2", id="btn-no2", n_clicks=0, color="primary", outline=True, style={'borderColor': 'white','borderRadius': '0', 'color': 'white'}),
                dbc.Button("O3", id="btn-o3", n_clicks=0, color="primary", outline=True, style={'borderColor': 'white','borderRadius': '0', 'color': 'white'}),
            ], className="d-flex justify-content-center")
        ),
         style={"background-color": "black", "padding":"10px"}
    ),
    html.Div(
        dbc.Container(
            # graph pollutants selector
            dcc.Dropdown(
                id='parameter-selector',
                options=[
                    {'label': 'PM 2.5', 'value': 'PM25'},
                    {'label': 'PM 10', 'value': 'PM10'},
                    {'label': 'O3', 'value': 'O3'},
                ],
                value='PM25',
                clearable=False,
                style={'width': '50%', 'margin': '20px auto'}
            ),
        ),
         style={"background-color": "black", "padding":"10px"}
    ),
    # forecast graph
    dcc.Graph(id='air-quality-graph'),
])

# define callback to update the graph based on map button clicks
@app.callback(
    Output('air-quality-map', 'figure'),
    [Input('btn-aqi', 'n_clicks'),
     Input('btn-pm25', 'n_clicks'),
     Input('btn-pm10', 'n_clicks'),
     Input('btn-no2', 'n_clicks'),
     Input('btn-o3', 'n_clicks'),]
)
def update_graph(n_clicks_aqi, n_clicks_pm25, n_clicks_pm10, n_clicks_no2, n_clicks_o3):
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    # define the initial range for the graph (pm25)
    pollutant_range = (0, 500)
    # for each pollutant there is different scale based on range and on the danger 
    pollutant_continuous_scale = [
    [0, 'rgb(0,255,0)'],       # green
    [0.024, 'rgb(255,255,0)'],  # yellow
    [0.071, 'rgb(255,165,0)'],   # orange
    [0.111, 'rgb(255,0,0)'],    # red
    [0.301, 'rgb(183, 36, 209)'], # purple
    [0.5, 'rgb(91, 41, 99)'], # grey purple
    [1, 'rgb(46, 31, 48)'] # dark purple
    ]
    # pm25 starting pollutant
    pollutant = 'pm25'
    if 'btn-pm25' in changed_id:
        pollutant = 'pm25'
        pollutant_range = (0, 500)
        pollutant_continuous_scale = [
        [0, 'rgb(0,255,0)'],       
        [0.024, 'rgb(255,255,0)'],  
        [0.071, 'rgb(255,165,0)'],  
        [0.111, 'rgb(255,0,0)'],    
        [0.301, 'rgb(183, 36, 209)'],
        [0.5, 'rgb(91, 41, 99)'],
        [1, 'rgb(46, 31, 48)']       
        ]
    elif 'btn-pm10' in changed_id:
        pollutant = 'pm10'
        pollutant_range = (0, 750)
        pollutant_continuous_scale = [
        [0, 'rgb(0,255,0)'],                       
        [0.027, 'rgb(255,255,0)'],  
        [0.054, 'rgb(255,165,0)'],   
        [0.067, 'rgb(255,0,0)'],    
        [0.134, 'rgb(183, 36, 209)'],
        [0.2, 'rgb(91, 41, 99)'],
        [1, 'rgb(46, 31, 48)']       
        ]
    elif 'btn-no2' in changed_id:
        pollutant = 'no2'
        pollutant_range = (0, 750)
        pollutant_continuous_scale = [
        [0, 'rgb(0,255,0)'],                     
        [0.02, 'rgb(255,255,0)'],  
        [0.035, 'rgb(255,165,0)'],   
        [0.047, 'rgb(255,0,0)'],   
        [0.06, 'rgb(183, 36, 209)'],
        [0.09, 'rgb(91, 41, 99)'],
        [1, 'rgb(46, 31, 48)']       
        ]
    elif 'btn-o3' in changed_id:
        pollutant = 'o3'
        pollutant_range = (0, 500)
        pollutant_continuous_scale = [
        [0, 'rgb(0,255,0)'],                      
        [0.1, 'rgb(255,255,0)'],  
        [0.2, 'rgb(255,165,0)'],   
        [0.26, 'rgb(255,0,0)'],    
        [0.48, 'rgb(183, 36, 209)'],
        [0.76, 'rgb(91, 41, 99)'],
        [1, 'rgb(46, 31, 48)']       
        ]
    elif 'btn-aqi' in changed_id:
        pollutant = 'aqi'
        pollutant_range = (0, 500)
        pollutant_continuous_scale = [
        [0, 'rgb(0,255,0)'],                    
        [0.1, 'rgb(255,255,0)'], 
        [0.2, 'rgb(255,165,0)'],   
        [0.3, 'rgb(255,0,0)'],   
        [0.4, 'rgb(183, 36, 209)'],
        [0.6, 'rgb(91, 41, 99)'],
        [1, 'rgb(46, 31, 48)']       
        ]
    
    # filter to avoid data errors
    filtered_df = merged_df[(merged_df[pollutant].notnull())&(merged_df[pollutant]>=0)&(merged_df[pollutant]!=9999)]
    # mapbox token
    px.set_mapbox_access_token("pk.eyJ1IjoiYW5keWJlbnoxNCIsImEiOiJjbHcwZXRjZmEwMDVuMmtwZGkxcTUxdTZ2In0.7oWJCrFtYShoIdAo_nAShg")
    fig = px.scatter_mapbox(filtered_df, lat="latitude", lon="longitude", color=pollutant, size="size",
                            color_continuous_scale = pollutant_continuous_scale,
                            range_color = pollutant_range,
                            hover_data={
                             "latitude": False, 
                             "longitude": False, 
                             "size": False, 
                             "city": True,
                             "last_updated": True,
                             pollutant: True,
                            },
                            mapbox_style="streets",
                            height=850, 
                            size_max=7, zoom=1.6, center={"lat": 25, "lon": 15})
    # customize map style
    fig.update_layout(
     margin=dict(r=0,b=0,t=0),
     paper_bgcolor="Black",
     height=850,
     font_color="white",
    )

    return fig

# second callback function for the second graph update
@app.callback(
    Output('air-quality-graph', 'figure'),
    [Input('air-quality-map', 'clickData'),
     Input('parameter-selector', 'value')]
)

# detect mouse click into map' location and calls API data request function
# for the selected location
def update_graph_from_click(clickData, parameter):
    if clickData and 'points' in clickData:
        # saves click coordinates
        point = clickData['points'][0]
        lat = point['lat']
        lon = point['lon']
        # api request function 
        api.get_aqi_value_from_api(lon, lat)
        # reads csv file generated by the function
        df = pd.read_csv('aqi_data.csv')
        # takes firs not null collumn info
        city = df['City'].dropna().iloc[0]  
        
        # maps parameters
        parameter_map = {
            'PM25': 'PM2.5',
            'PM10': 'PM10',
            'O3': 'O3'
        }
        
        # selectes the selected parameter collumn
        selected_column = parameter_map[parameter]
        
        # creates graph
        fig = go.Figure()

        # custom graph background-range-color for each pollutant based on the danger
        if(parameter=='PM25'):
            max_y_value = df['Max PM2.5'].max()
            fig.add_shape(type="rect", xref="paper", yref="y",
                         x0=0, y0=0, y1=12, x1=1, layer="below",
                        fillcolor="green", opacity=0.35, line_width=0)
            if(max_y_value > 12):
                fig.add_shape(type="rect", xref="paper", yref="y",
                            x0=0, y0=12, y1=35, x1=1, layer="below",
                            fillcolor="yellow", opacity=0.35, line_width=0)
                if(max_y_value > 35):
                    fig.add_shape(type="rect", xref="paper", yref="y",
                                x0=0, y0=35, y1=55, x1=1, layer="below",
                                fillcolor="orange", opacity=0.35, line_width=0)
                    if(max_y_value > 55):
                        fig.add_shape(type="rect", xref="paper", yref="y",
                                    x0=0, y0=55, y1=max_y_value+10, x1=1, layer="below",
                                    fillcolor="red", opacity=0.35, line_width=0)
        elif(parameter=='PM10'):
            max_y_value = df['Max PM10'].max()
            fig.add_shape(type="rect", xref="paper", yref="y",
                         x0=0, y0=0, y1=20, x1=1, layer="below",
                        fillcolor="green", opacity=0.35, line_width=0)
            if(max_y_value > 20):
                fig.add_shape(type="rect", xref="paper", yref="y",
                            x0=0, y0=20, y1=40, x1=1, layer="below",
                            fillcolor="yellow", opacity=0.35, line_width=0)
                if(max_y_value > 40):
                    fig.add_shape(type="rect", xref="paper", yref="y",
                                x0=0, y0=40, y1=60, x1=1, layer="below",
                                fillcolor="orange", opacity=0.35, line_width=0)
                    if(max_y_value > 60):
                        fig.add_shape(type="rect", xref="paper", yref="y", 
                                    x0=0, y0=60, y1=max_y_value+10, x1=1, layer="below",
                                    fillcolor="red", opacity=0.35, line_width=0)
        elif(parameter=='O3'):
            max_y_value = df['Max O3'].max()
            fig.add_shape(type="rect", xref="paper", yref="y",
                         x0=0, y0=0, y1=38, x1=1, layer="below",
                        fillcolor="green", opacity=0.35, line_width=0)
            if(max_y_value > 38):
                fig.add_shape(type="rect", xref="paper", yref="y",
                            x0=0, y0=38, y1=100, x1=1, layer="below",
                            fillcolor="yellow", opacity=0.35, line_width=0)
                if(max_y_value > 100):
                    fig.add_shape(type="rect", xref="paper", yref="y",
                                x0=0, y0=100, y1=130, x1=1, layer="below",
                                fillcolor="orange", opacity=0.35, line_width=0)
                    if(max_y_value > 130):
                        fig.add_shape(type="rect", xref="paper", yref="y",
                                    x0=0, y0=130, y1=max_y_value+10, x1=1, layer="below",
                                    fillcolor="red", opacity=0.35, line_width=0)

        # adding graph lines          
        fig.add_trace(go.Scatter(x=df['Time'], y=df[f'Max {selected_column}'], mode='lines', name=f'Max {selected_column}', line=dict(color='black')))    
        fig.add_trace(go.Scatter(x=df['Time'], y=df[f'Avg {selected_column}'], mode='lines', name=f'Avg {selected_column}', line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=df['Time'], y=df[f'Min {selected_column}'], mode='lines', name=f'Min {selected_column}', line = dict(color='purple')))

        # graph layout
        fig.update_layout(title=f'Air Quality forecast in {city}',
                          xaxis_title='Date',
                          yaxis_title='μg/m3',
                          legend_title=selected_column,
                          yaxis=dict(gridcolor='lightgrey', gridwidth=0.2),
                          xaxis=dict(gridcolor='lightgrey', gridwidth=0.2)
                          )
        # layout
        fig.update_layout(
            margin=dict(t=50),
            paper_bgcolor="Black",
            font_color="white",
        )
        
        return fig

    return go.Figure(layout=go.Layout(paper_bgcolor="Black", font_color="white"))

# run the app
if __name__ == '__main__':
    app.run_server(debug=False)




