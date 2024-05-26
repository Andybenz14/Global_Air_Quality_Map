import pandas as pd
import plotly.express as px
import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import requests
import csv
import plotly.graph_objs as go

                
# fetching data using area search (waqi API)
# uses this method to bypass the limit of rows 
# that can be removed per second from the server (1000)
def fetch_data(token, lat_min, lon_min, lat_max, lon_max):
    url = f"https://api.waqi.info/map/bounds/?token={token}&latlng={lat_min},{lon_min},{lat_max},{lon_max}"
    response = requests.get(url)
    return response.json()
    
# token to access data from da API
token = "4e18987328d2ba9e1e5076e65fbaba8ec7e18d97"

# search boxes
searching_boxes = [
    (-90, -180, 0, 0),
    (-90, 0, 0, 180),
    (0, -180, 90, 0),
    (0, 0, 90, 180)
]

# sub boxes
sub_searching_boxes = [
    [(-90, -180, -45, 0), (-90, 0, -45, 180), (-45, -180, 0, 0), (-45, 0, 0, 180)],
    [(-90, 0, -45, 90), (-90, 90, -45, 180), (-45, 0, 0, 90), (-45, 90, 0, 180)],
    [(0, -180, 45, 0), (0, 0, 45, 180), (45, -180, 90, 0), (45, 0, 90, 180)],
    [(0, 0, 45, 90), (0, 90, 45, 180), (45, 0, 90, 90), (45, 90, 90, 180)]
]

# fetch data for each sub-bounding box
all_data = []
for i, box in enumerate(searching_boxes):
    sub_boxes = sub_searching_boxes[i]
    for sub_box in sub_boxes:
        data = fetch_data(token, *sub_box)
        if data['status'] == 'ok':
            all_data.extend(data['data'])

extracted_data = []

# selected usefull data
for result in all_data:
    station_name = result.get("station", {}).get("name", "Unknown")
    latitude = result.get("lat", None)
    longitude = result.get("lon", None)
    last_updated = result.get("station", {}).get("time", None)
    aqi_measurement = result.get("aqi", None)
    # remove useless info
    if aqi_measurement != '-':    
        aqi_value = aqi_measurement
    else:
        aqi_value = 0
    
    # include all relevant values in result_data
    result_data = {
        'location': station_name,
        'latitude': latitude,
        'longitude': longitude,
        'aqi': aqi_value,
        'last_updated': last_updated,
        'size': 1
    }
    # all the selected data
    extracted_data.append(result_data)

# create DataFrame
df0 = pd.DataFrame(extracted_data)

# convert dataframe to csv file
df0.to_csv("world_air_quality_data_AQI.csv", index=False)


# fecthing data from openaq API
url = "https://api.openaq.org/v2/latest?limit=10000&page=1&offset=0&sort=desc&radius=1000&order_by=lastUpdated&dump_raw=false"


headers = {
    "accept": "application/json",
    "content-type": "application/json"
}

response = requests.get(url, headers=headers)
data = response.json()
results = data['results']
extracted_data = []

# selected usefull data
for result in results:
    parameters = result['measurements']
    pm25_value = next((p['value'] for p in parameters if p['parameter'] == 'pm25'), None)
    pm10_value = next((p['value'] for p in parameters if p['parameter'] == 'pm10'), None)
    no2_measurement = next((p for p in parameters if p['parameter'] == 'no2'), None)
    # filter ppm unit
    if no2_measurement is not None and isinstance(no2_measurement, dict):
        if 'unit' in no2_measurement and no2_measurement['unit'] == 'ppm':
            # conversion from ppm to µg/m³ for no2 at air temperature
            no2_value = no2_measurement['value'] * 1882 
        else:
            no2_value = no2_measurement['value']
    else:
        no2_value = None
    o3_measurement = next((p for p in parameters if p['parameter'] == 'o3'), None)
    # filter ppm unit
    if o3_measurement is not None and isinstance(o3_measurement, dict):
        if 'unit' in o3_measurement and o3_measurement['unit'] == 'ppm':
             # conversion from ppm to µg/m³ for o3 at air temperature
            o3_value = o3_measurement['value'] * 1963 * 0.43
        else:
            o3_value = o3_measurement['value'] * 0.43
    else:
        o3_value = None
    last_updated = max([p['lastUpdated'] for p in parameters]) 

    # save data only if there is at least one pollutant info
    if (pm25_value or pm10_value or no2_value or o3_value) is not None:
        result_data = {
            'location': result['location'],
            'country': result['country'],
            'city': result['city'],
            'latitude': result['coordinates']['latitude'],
            'longitude': result['coordinates']['longitude'],
            'pm25': pm25_value,
            'pm10': pm10_value,
            'no2': no2_value,  
            'o3': o3_value,
            'last_updated': last_updated,
            'size': 1
        }
        extracted_data.append(result_data)

# create a DataFrame with the extracted data
df = pd.DataFrame(extracted_data)

# save the DataFrame into a CSV file (CSV file is unnecessary, but in this case
# it's usefull to read the big amount of data and check fast if the latest data
# are arrived from the API)
df.to_csv("openaq_data_with_pm10.csv", index=False)

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

def get_aqi_value_from_api(lon, lat):
    url = f"https://api.waqi.info/feed/geo:{lat};{lon}/?token={token}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        aqi_data = data.get('data', {})
        if aqi_data:
            # Estrai i dati sull'AQI
            idx = aqi_data.get('idx', '')
            aqi = aqi_data.get('aqi', '')
            time_info = aqi_data.get('time', {})
            city_info = aqi_data.get('city', {})
            forecast_data_pm25 = aqi_data.get('forecast', {}).get('daily', {}).get('pm25', [])
            forecast_data_pm10 = aqi_data.get('forecast', {}).get('daily', {}).get('pm10', [])
            forecast_data_o3 = aqi_data.get('forecast', {}).get('daily', {}).get('o3', [])
            # Scrivi i dati in un file CSV
            with open('aqi_data.csv', mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(['Index', 'AQI', 'Time', 'City', 'PM2.5', 'Avg PM2.5', 'Max PM2.5', 'Min PM2.5', 'PM10' ,'Avg PM10', 'Max PM10', 'Min PM10','O3', 'Avg O3', 'Max O3', 'Min O3'])
                writer.writerow([idx, aqi, time_info.get('s', ''), city_info.get('name', '')])
                for day_data in forecast_data_pm25:
                    avg_pm25 = day_data.get('avg', '')
                    max_pm25 = day_data.get('max', '')
                    min_pm25 = day_data.get('min', '')
                    writer.writerow(['', '', day_data.get('day', ''), '', '', avg_pm25, max_pm25, min_pm25])
                for day_data in forecast_data_pm10:
                    avg_pm10 = day_data.get('avg', '')
                    max_pm10 = day_data.get('max', '')
                    min_pm10 = day_data.get('min', '')
                    writer.writerow(['', '', day_data.get('day', ''), '', '','','','', '', avg_pm10, max_pm10, min_pm10])
                for day_data in forecast_data_o3:
                    avg_o3 = day_data.get('avg', '')
                    max_o3 = day_data.get('max', '')
                    min_o3 = day_data.get('min', '')
                    writer.writerow(['', '', day_data.get('day', ''), '', '','','','','','','','','', avg_o3, max_o3, min_o3])
    



# initialize the Dash app
app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

# create the layout of the app
app.layout = html.Div([
    dbc.NavbarSimple(
        brand="World Air Quality Map",
        brand_href="#",
        color="Black",
        dark=True,
    ),
    dcc.Graph(id='air-quality-map', style={"margin-bottom": "0px"}),
    html.Div(
        dbc.Container(
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

    dcc.Graph(id='air-quality-graph'),
])

# define callback to update the graph based on button clicks
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
 
    fig.update_layout(
     margin=dict(r=0,b=0,t=0),
     paper_bgcolor="Black",
     height=850,
     font_color="white",
    )

    global global_variable
    global_variable = pollutant
    return fig

@app.callback(
    Output('air-quality-graph', 'figure'),
    [Input('air-quality-map', 'clickData'),
     Input('parameter-selector', 'value')]
)

def update_graph_from_click(clickData, parameter):
    if clickData and 'points' in clickData:
        point = clickData['points'][0]
        lat = point['lat']
        lon = point['lon']
        get_aqi_value_from_api(lon, lat)
        df = pd.read_csv('aqi_data.csv')
        city = df['City'].dropna().iloc[0]  # Prende la prima occorrenza non nulla della colonna City
        
        # Mappa il parametro selezionato alla colonna corrispondente
        parameter_map = {
            'PM25': 'PM2.5',
            'PM10': 'PM10',
            'O3': 'O3'
        }
        
        selected_column = parameter_map[parameter]
        
        # Crea il grafico
        fig = go.Figure()

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
                        
        fig.add_trace(go.Scatter(x=df['Time'], y=df[f'Max {selected_column}'], mode='lines', name=f'Max {selected_column}', line=dict(color='black')))    
        fig.add_trace(go.Scatter(x=df['Time'], y=df[f'Avg {selected_column}'], mode='lines', name=f'Avg {selected_column}', line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=df['Time'], y=df[f'Min {selected_column}'], mode='lines', name=f'Min {selected_column}', line = dict(color='purple')))

        # Aggiungi layout e etichette
        fig.update_layout(title=f'Air Quality forecast in {city}',
                          xaxis_title='Date',
                          yaxis_title='μg/m3',
                          legend_title=selected_column,
                          yaxis=dict(gridcolor='lightgrey', gridwidth=0.2),
                          xaxis=dict(gridcolor='lightgrey', gridwidth=0.2)
                          )
        
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




