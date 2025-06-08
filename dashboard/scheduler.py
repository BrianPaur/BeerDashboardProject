from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import requests
from django.utils.timezone import now
from .models import TemperatureData

from tuya_connector import TuyaOpenAPI
from dashboard.creds.creds import ACCESS_ID, ACCESS_KEY, ENDPOINT, DEVICE_ID

def data_update():
    openapi = TuyaOpenAPI(ENDPOINT, ACCESS_ID, ACCESS_KEY)
    connection = openapi.connect()

    data = openapi.get(F"/v1.0/iot-03/devices/{DEVICE_ID}/status")
    temp_data = TemperatureData(
        time_stamp=datetime.datetime.now(),
        current_temp=data['result'][3]['value'] / 10,
        set_temp=data['result'][2]['value'] / 10,
    )
    temp_data.save()


def start_data_update():
    scheduler = BackgroundScheduler()
    scheduler.add_job(data_update, 'interval', minutes=15)
    scheduler.start()
    
