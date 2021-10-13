import configparser
import requests
import json
import datetime

config = configparser.ConfigParser()
config.read("config.ini")
key = config["DEFAULT"]["key"]
user = config["DEFAULT"]["user_id"]
system = config["DEFAULT"]["system"]

url = (
    "https://api.enphaseenergy.com/api/v2/systems/"
    + system
    + "/summary?key="
    + key
    + "&user_id="
    + user
)

payload = {}
headers = {}

response = requests.request("GET", url, headers=headers, data=payload)
respjson = json.loads(response.text)
lastreport = datetime.datetime.fromtimestamp(int(respjson["last_report_at"]))
status = respjson["status"]

print(f"Energy collected today: {(respjson['energy_today'])}")
print(f"Last reported on {lastreport}")
print(f"Solar array status is '{status}'.")
