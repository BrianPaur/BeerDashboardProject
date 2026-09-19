from django.core.management.base import BaseCommand
from django.utils import timezone

from dashboard.models import TemperatureData
from dashboard.services.inkbird import InkbirdService
from dashboard.creds.creds import DEVICE_ID


class Command(BaseCommand):
    help = "Collect the current Inkbird temperature and save it to the database."

    def handle(self, *args, **options):
        try:
            inkbird = InkbirdService(DEVICE_ID)

            current_temp = inkbird.get_temperature()
            set_temp = inkbird.get_target_temperature()

            reading = TemperatureData.objects.create(
                time_stamp=timezone.now(),
                current_temp=current_temp,
                set_temp=set_temp,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Temperature reading saved: "
                    f"current={reading.current_temp}, "
                    f"set={reading.set_temp}"
                )
            )

        except Exception as exc:
            self.stderr.write(
                self.style.ERROR(
                    f"Unable to collect temperature data: {exc}"
                )
            )