
ACCESS_ID = 'm3unsvjm9anyxxypgw3n'
ACCESS_KEY = 'f628aa4e7cb446dea01c6ede767d9f4d'
USERNAME = "brian.paur@gmail.com"
PASSWORD = "TortoiseTuya1992!!"
DEVICE_ID = 'eb10c2cc70ba8df777tmda'
DEVICE_IP = '136.32.198.207'
ENDPOINT = "https://openapi.tuyaus.com"
MQ_ENDPOINT = "wss://mqe.tuyacn.com:8285/"
ASSET_ID = 'fermentation_control'
SELECTQUERY = "SELECT * FROM beerdata"
QUERY = """
CREATE TABLE IF NOT EXISTS beerdata (
id INTEGER PRIMARY KEY AUTOINCREMENT,
timestamp TEXT,
settemp INTEGER,
currenttemp INTEGER
);
"""
