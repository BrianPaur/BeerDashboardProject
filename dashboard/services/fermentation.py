from decimal import Decimal, ROUND_HALF_UP

import numpy as np

from dashboard.models import FermentationDataTilt

class FermentationService:
    """Service for fermentation-related calculations and analysis."""

    @staticmethod
    def calculate_abv(original_gravity, final_gravity):
        """Calculate approximate ABV from OG and FG."""

        if original_gravity is None or final_gravity is None:
            return None

        abv = (
                original_gravity - final_gravity
        ) * Decimal("131.25")

        return abv.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def calculate_attenuation(original_gravity, final_gravity):
        """Calculate apparent attenuation percentage."""

        if original_gravity is None or final_gravity is None:
            return None

        if original_gravity == Decimal("1"):
            return None

        attenuation = (
                (original_gravity - final_gravity)
                / (original_gravity - Decimal("1"))
        ) * Decimal("100")

        return attenuation.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def calculate_duration(start_time, end_time):
        """Return fermentation duration as a human-readable string."""
        if start_time is None or end_time is None:
            return None

        duration = end_time - start_time

        total_minutes = int(duration.total_seconds() // 60)

        days = total_minutes // (24 * 60)
        hours = (total_minutes % (24 * 60)) // 60
        minutes = total_minutes % 60

        return f"{days}:{hours}:{minutes}"

    @staticmethod
    def calculate_gravity_change(
        original_gravity,
        current_gravity,
    ):
        """Return the change in specific gravity."""

        if original_gravity is None or current_gravity is None:
            return None

        return original_gravity - current_gravity

    @staticmethod
    def get_readings(batch_name):
        """Return Tilt readings for a batch in chronological order."""

        return (
            FermentationDataTilt.objects
            .filter(name=batch_name)
            .order_by("timestamp")
        )

    @staticmethod
    def get_gravity_readings(batch_name):
        """Return timestamp/gravity pairs for a batch."""

        readings = FermentationService.get_readings(batch_name)

        return [
            (reading.timestamp, reading.gravity)
            for reading in readings
            if reading.gravity is not None
        ]

    @staticmethod
    def get_active_readings(batch_name):
        """Return Tilt readings that fall within the active fermentation period."""

        start_time, end_time = (
            FermentationService.get_fermentation_period(batch_name)
        )

        if start_time is None or end_time is None:
            return []

        readings = FermentationService.get_readings(batch_name)

        return [
            reading
            for reading in readings
            if start_time <= reading.timestamp <= end_time
        ]

    @staticmethod
    def calculate_gravity_slope(batch_name):
        """
        Calculate gravity slope during active fermentation.

        Returns gravity points per day.
        """

        active_readings = FermentationService.get_active_readings(
            batch_name
        )

        if len(active_readings) < 2:
            return None

        timestamps = [
            reading.timestamp
            for reading in active_readings
        ]

        gravities = [
            float(reading.gravity)
            for reading in active_readings
        ]

        first_time = timestamps[0]

        x_data = [
            (timestamp - first_time).total_seconds() / 86400
            for timestamp in timestamps
        ]

        y_data = gravities

        x_mean = np.mean(x_data)
        y_mean = np.mean(y_data)

        numerator = np.sum(
            (np.array(x_data) - x_mean)
            * (np.array(y_data) - y_mean)
        )

        denominator = np.sum(
            (np.array(x_data) - x_mean) ** 2
        )

        if denominator == 0:
            return None

        slope = numerator / denominator

        return slope

    @staticmethod
    def get_fermentation_period(batch_name):
        """
        Determine the start and end timestamps of active fermentation.
        """

        readings = FermentationService.get_gravity_readings(batch_name)

        if len(readings) < 2:
            return None, None

        timestamps = [reading[0] for reading in readings]
        gravities = [reading[1] for reading in readings]

        # Find when fermentation actually starts
        gravity_drop_threshold = 0.002
        consecutive_drops = 5

        fermentation_start_index = 0

        for i in range(len(gravities) - consecutive_drops):

            max_gravity_so_far = max(gravities[:i + 1])

            is_sustained_drop = True

            for j in range(consecutive_drops):

                if i + j >= len(gravities):
                    is_sustained_drop = False
                    break

                if (
                        float(gravities[i + j])
                        >= float(max_gravity_so_far) - gravity_drop_threshold
                ):
                    is_sustained_drop = False
                    break

            if is_sustained_drop:
                fermentation_start_index = i
                break

        # Find when fermentation stops
        fermentation_end_index = len(gravities) - 1

        stability_threshold = 0.001
        consecutive_stable = 10

        for i in range(
                len(gravities) - consecutive_stable,
                fermentation_start_index,
                -1
        ):

            is_stable = True

            for j in range(consecutive_stable - 1):

                if i + j + 1 >= len(gravities):
                    is_stable = False
                    break

                gravity_change = abs(
                    float(gravities[i + j])
                    - float(gravities[i + j + 1])
                )

                if gravity_change > stability_threshold:
                    is_stable = False
                    break

            if is_stable:
                fermentation_end_index = i
                break

        # Check whether fermentation has actually started
        if fermentation_start_index == 0:

            if (
                    float(gravities[0])
                    - float(gravities[-1])
                    < gravity_drop_threshold
            ):
                return None, None

        start_time = timestamps[fermentation_start_index]
        end_time = timestamps[fermentation_end_index]

        return start_time, end_time

    @staticmethod
    def get_latest_reading(batch_name):
        """Return the latest Tilt reading for a batch."""

        return (
            FermentationDataTilt.objects
            .filter(name=batch_name)
            .order_by("-timestamp")
            .first()
        )

    @staticmethod
    def calculate_fermentation_duration(batch_name):
        """Calculate the duration of active fermentation for a batch."""
        start_time, end_time = (
            FermentationService.get_fermentation_period(batch_name)
        )

        return FermentationService.calculate_duration(
            start_time,
            end_time,
        )




