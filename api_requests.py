import pandas as pd
import plotly.express as px
import requests
import csv

# token to access data from da API
token = "4e18987328d2ba9e1e5076e65fbaba8ec7e18d97"

# fetching data using area search (waqi API)
# uses this method to bypass the limit of rows 
# that can be taken per second from the server (1000)
def fetch_data(token, lat_min, lon_min, lat_max, lon_max):
    url = f"https://api.waqi.info/map/bounds/?token={token}&latlng={lat_min},{lon_min},{lat_max},{lon_max}"
    response = requests.get(url)
    # return extracted data
    return response.json()


def firstapi_data_extraction():

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
    # data vector initiliation
    all_data = []
    for i, box in enumerate(searching_boxes):
        sub_boxes = sub_searching_boxes[i]
        for sub_box in sub_boxes:
            # ask data to the API using the selected box as parameter
            data = fetch_data(token, *sub_box)
            if data['status'] == 'ok':
                # adding data to the data vector
                all_data.extend(data['data'])

    # data vector initiliation
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
        # adding selected data to data vector
        extracted_data.append(result_data)

    # create DataFrame
    df0 = pd.DataFrame(extracted_data)

    # convert dataframe to csv file
    csv_path0 = "waqi_data.csv"
    df0.to_csv(csv_path0, index=False)

    return csv_path0


def secondapi_data_extraction():
        
    # second API data request
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
        # selected pollutants values
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
                # conversion from ppm to µg/m³ for o3 at air temperature + normalize
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

    # save the DataFrame into a CSV file ( creates CSV file to use it 
    # shared trought modules, to read easily the big amount of data and 
    # check fast if the latest date are arrived from the API)
    csv_path1 = "openaq_data.csv"
    df.to_csv(csv_path1, index=False)

    return csv_path1

 
# called by mouse click into a location on the map 
# request to the API the forecast data for the clicked location
def get_aqi_value_from_api(lon, lat):
    url = f"https://api.waqi.info/feed/geo:{lat};{lon}/?token={token}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        aqi_data = data.get('data', {})
        if aqi_data:
            # extract data 
            idx = aqi_data.get('idx', '')
            aqi = aqi_data.get('aqi', '')
            time_info = aqi_data.get('time', {})
            city_info = aqi_data.get('city', {})
            forecast_data_pm25 = aqi_data.get('forecast', {}).get('daily', {}).get('pm25', [])
            forecast_data_pm10 = aqi_data.get('forecast', {}).get('daily', {}).get('pm10', [])
            forecast_data_o3 = aqi_data.get('forecast', {}).get('daily', {}).get('o3', [])
            # writes data into a csv file
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