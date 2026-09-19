import json
from tuya_connector import TuyaOpenAPI

with open('/etc/secrets/creds.json') as f:
    creds = json.load(f)

ACCESS_ID = creds['ACCESS_ID']
ACCESS_KEY = creds['ACCESS_KEY']
ENDPOINT = creds['ENDPOINT']
DEVICE_ID = creds['DEVICE_ID']
DEVICE_ID2 = creds['DEVICE_ID2']


class InkbirdService:
    """Service for communicating with Inkbird temperature controllers via Tuya."""
    def __init__(self, device_id):
        self.device_id = device_id
        self.openapi = TuyaOpenAPI(
            ENDPOINT,
            ACCESS_ID,
            ACCESS_KEY,
        )
        self.openapi.connect()
        self._status_data = None

    def getStatusData(self):
        """Get and cache the current device status."""
        if self._status_data is None:
            response = self.openapi.get(
                f"/v1.0/iot-03/devices/{self.device_id}/status"
            )

            if not response.get("success"):
                raise RuntimeError(
                    f"Unable to retrieve Inkbird status: "
                    f"{response.get('msg', 'Unknown error')}"
                )

            self._status_data = response

        return self._status_data

    def get_temperature(self):
        """Return the current temperature in °F."""
        data = self.getStatusData()
        return data["result"][3]["value"] / 10

    def get_target_temperature(self):
        """Return the current target temperature in °F."""
        data = self.getStatusData()
        return data["result"][2]["value"] / 10

    def set_temperature(self, temperature):
        """Set the Inkbird target temperature in °F."""
        commands = {
            "commands": [
                {
                    "code": "temp_set",
                    "value": int(temperature * 10),
                }
            ]
        }

        response = self.openapi.post(
            f"/v1.0/iot-03/devices/{self.device_id}/commands",
            commands,
        )

        if not response.get("success"):
            raise RuntimeError(
                f"Unable to set Inkbird temperature: "
                f"{response.get('msg', 'Unknown error')}"
            )

        # Clear cached status so the next read gets fresh data
        self._status_data = None

        return temperature