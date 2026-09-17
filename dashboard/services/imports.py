import csv

from dateutil import parser
from django.utils import timezone

from dashboard.models import FermentationDataTilt

class ImportService:
    """ Service for importing fermentation data. """

    @staticmethod
    def import_tilt_csv(csv_file):
        """
        Import Tilt CSV data into the database

        CSV parsing and database logic will be moved here incrementally
        """

        decoded_file = (
            csv_file.read()
            .decode("utf-8")
            .splitlines()
        )

        reader = csv.DictReader(decoded_file)

        success_count = 0
        error_count = 0
        errors = []

        for row_num, row in enumerate(reader, start=2):
            try:
                # Support old and new column formats
                name = row.get("Beer") or row.get("name", "Unknown")
                name = name.strip() if name else "Unknown"

                temperature = float(
                    row.get("Temp")
                    or row.get("temperature", 0)
                )

                gravity = float(
                    row.get("SG")
                    or row.get("gravity", 0)
                )

                color = row.get("Color") or row.get("color", "")
                color = color.strip() if color else ""

                timestamp_str = (
                    row.get("Time")
                    or row.get("timestamp", "")
                )

                timestamp_str = (
                    timestamp_str.strip()
                    if timestamp_str
                    else ""
                )

                comment = (
                    row.get("Comment")
                    or row.get("comment", "")
                )

                comment = comment.strip() if comment else ""

                # Parse timestamp
                if timestamp_str:
                    timestamp = parser.parse(timestamp_str)
                else:
                    timestamp = timezone.now()

                # Create database record
                FermentationDataTilt.objects.create(
                    name=name,
                    temperature=temperature,
                    gravity=gravity,
                    color=color,
                    timestamp=timestamp,
                    comment=comment,
                )

                success_count += 1

            except Exception as error:
                error_count += 1
                errors.append(
                    f"Row {row_num}: {str(error)}"
                )

        return {
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors,
        }