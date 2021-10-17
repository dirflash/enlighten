__author__ = "Aaron Davis"
__version__ = "0.1.0"
__copyright__ = "Copyright (c) 2021 Aaron Davis"
__license__ = "MIT License"

import configparser
import requests
import json
import time
from datetime import datetime, timedelta
import certifi
import pymongo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

if __name__ == "__main__":

    start_time = time.time()
    current_epoch = int(time.time())

    config = configparser.ConfigParser()
    config.read("config.ini")
    key = config["DEFAULT"]["key"]
    user = config["DEFAULT"]["user_id"]
    system = config["DEFAULT"]["system"]
    mongoaddr = config["MONGO"]["mongo_addr"]
    mongodb = config["MONGO"]["mongo_db"]
    mongocollect = config["MONGO"]["mongo_collect"]
    mongouser = config["MONGO"]["user_name"]
    mongopw = config["MONGO"]["password"]

    maxMongoDBDelay = 500

    url = (
        "https://api.enphaseenergy.com/api/v2/systems/"
        + system
        + "/summary?key="
        + key
        + "&user_id="
        + user
    )

    client = MongoClient(
        "mongodb+srv://"
        + mongouser
        + ":"
        + mongopw
        + "@"
        + mongoaddr
        + "/"
        + mongodb
        + "?retryWrites=true&w=majority",
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=maxMongoDBDelay,
    )

    db = client[mongodb]
    collection = db[mongocollect]

    payload = {}
    headers = {}

    while True:
        response = requests.request("GET", url, headers=headers, data=payload)
        respjson = json.loads(response.text)
        epochlastreport = respjson["last_report_at"]
        lastreport = datetime.fromtimestamp(int(respjson["last_report_at"]))
        status = respjson["status"]
        collected = respjson["energy_today"]

        lastreportdelta = (current_epoch - epochlastreport) / 60

        if lastreportdelta < 86400:
            range = True
        else:
            range = False

        print(f"Energy collected today: {collected}")
        print(f"Last reported on (epoch): {epochlastreport}")
        print(f"Current time (epoch): {current_epoch}")
        print(f"Epoch delta: {current_epoch - epochlastreport}")
        print(f"Last reported on: {lastreport}")
        print(f"Time since last reported (mins): %.3f" % lastreportdelta)
        print(f"Solar array status: {status}")
        print(f"In range? {range}")

        try:
            client.admin.command("ping")
        except ConnectionFailure:
            print("Server not available")

        try:
            insert = {
                "EpochLastReport": epochlastreport,
                "LastReport": lastreport,
                "Collected": collected,
                "Status": status,
                "Reporting": range,
            }
            post = collection.insert_one(insert)
            print("Created record as {0}".format(post.inserted_id))
        except pymongo.errors.ServerSelectionTimeoutError as err:
            print(err)

        print("--- Script ran in %.3f seconds ---" % (time.time() - start_time))

        ennext = datetime.now() + timedelta(seconds=14400)
        nextrun = ennext.strftime("%m-%d-%Y %H:%M:%S")
        print(f"--- Next run: {nextrun} ---")

        time.sleep(14400)
