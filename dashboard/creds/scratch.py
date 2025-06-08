import gspread
import pandas as pd
# from BeerDashboard.dashboard.models import FermentationData
from BeerDashboard.dashboard.creds.creds import ACCESS_ID, ACCESS_KEY, ENDPOINT, DEVICE_ID
from tuya_connector import TuyaOpenAPI

openapi = TuyaOpenAPI(ENDPOINT, ACCESS_ID, ACCESS_KEY)
connection = openapi.connect()


# gc = gspread.service_account(filename='C:/Users/Brian/PycharmProjects/BeerDjangoController/.venv/BeerDashboard/dashboard/creds/credentials.json')
#
#
#
# sh = gc.open("American Wheat Ale 1 (RED TILT)")
#
# worksheet = sh.worksheet("Data")

# current_gravity = sh.worksheet("Report").acell('B8').value
# starting_gravity = sh.worksheet("Report").acell('B9').value
# ferm_rate = sh.worksheet("Report").acell('B10').value
# duration_grav = sh.worksheet("Report").acell('B11').value
# high_gravity = sh.worksheet("Report").acell('B12').value
# low_gravity = sh.worksheet("Report").acell('B13').value
# current_temp = sh.worksheet("Report").acell('B15').value
# average_temp = sh.worksheet("Report").acell('B16').value
# duration_days = sh.worksheet("Report").acell('B17').value
# high_temp = sh.worksheet("Report").acell('B18').value
# low_temp = sh.worksheet("Report").acell('B19').value
# apparent_attenuation = sh.worksheet("Report").acell('B21').value
# abv = sh.worksheet("Report").acell('B22').value
# days_at_current_grav = sh.worksheet("Report").acell('B23').value

# def data_update():
#     list_of_lists = worksheet.get('A2:G2972')
#     df = pd.DataFrame(list_of_lists)
#     df.columns = ['Timestamp','Timepoint','SG','Temp','Color','Beer','Comment']
#     df['Timestamp'] = pd.to_datetime(df['Timestamp'])
#     df = df[df['Timestamp'] >= pd.to_datetime('12/2/2024')]
#     df = df.to_dict(orient='records')
#
#     print(df)

class TempControl:
    def __init__(self, current_temp=None, temp_goal=None):
        self.current_temp = current_temp
        self.temp_goal = temp_goal

    def temp_reading(self):
        data_pull = openapi.get(F"/v1.0/iot-03/devices/{DEVICE_ID}/status")
        self.current_temp = data_pull['result'][3]['value'] / 10
        return self.current_temp

    def temp_set_to(self):
        data_pull = openapi.get(F"/v1.0/iot-03/devices/{DEVICE_ID}/status")
        self.temp_goal = data_pull['result'][2]['value'] / 10
        return self.temp_goal

    def set_temp(self, temp):
        commands = {"commands": [{"code": "temp_set", "value": temp * 10}]}
        data_set = openapi.post(f"/v1.0/iot-03/devices/{DEVICE_ID}/commands", commands)
        return data_set

a = TempControl()
print(a.temp_reading())
print(type(70))














