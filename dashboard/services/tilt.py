from django.utils import timezone
from dateutil import parser

from dashboard.models import FermentationDataTilt


class TiltService:

    """Service for handling Tilt hydrometer data."""

    @staticmethod
    def save_reading(
        name,
        temperature,
        gravity,
        color="",
        timestamp=None,
        comment="",
    ):

        """Save a Tilt reading to the database."""

        if timestamp is None:
            timestamp = timezone.now()

        return FermentationDataTilt.objects.create(
            name=name,
            temperature=temperature,
            gravity=gravity,
            color=color,
            timestamp=timestamp,
            comment=comment,
        )

    @staticmethod
    def get_latest_reading(batch_name=None):
        """Return the latest Tilt reading, optionally for a specific batch."""

        readings = FermentationDataTilt.objects.all()

        if batch_name:
            readings = readings.filter(name=batch_name)

        return readings.order_by("-timestamp").first()

    @staticmethod
    def get_batch_readings(batch_name):
        """Return all readings for a batch in chronological order."""

        return (
            FermentationDataTilt.objects
            .filter(name=batch_name)
            .order_by("timestamp")
        )

    @staticmethod
    def get_batch_names():
        """Return distinct Tilt batch names."""

        return (
            FermentationDataTilt.objects
            .values_list("name", flat=True)
            .distinct()
            .exclude(name="")
            .order_by("name")
        )

    @staticmethod
    def parse_timestamp(timestamp_string):
        """Parse a Tilt timestamp string."""

        if not timestamp_string:
            return timezone.now()

        return parser.parse(timestamp_string)