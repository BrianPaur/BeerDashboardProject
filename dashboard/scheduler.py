from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone

from .models import TemperatureData
from .services.inkbird import InkbirdService
from dashboard.creds.creds import DEVICE_ID


def data_update():
    """
    Retrieve the current Inkbird temperature data and save
    a historical reading to the database.
    """
    try:
        inkbird = InkbirdService(DEVICE_ID)

        current_temp = inkbird.get_temperature()
        set_temp = inkbird.get_target_temperature()

        TemperatureData.objects.create(
            time_stamp=timezone.now(),
            current_temp=current_temp,
            set_temp=set_temp,
        )

    except Exception as exc:
        print(f"Unable to save Inkbird temperature data: {exc}")


def start_data_update():
    scheduler = BackgroundScheduler()

    scheduler.add_job(
        data_update,
        "interval",
        minutes=15,
    )

    scheduler.start()