import configparser
import requests
import json
import datetime
import certifi
import pymongo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

if __name__ == "__main__":

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

    response = requests.request("GET", url, headers=headers, data=payload)
    respjson = json.loads(response.text)
    lastreport = datetime.datetime.fromtimestamp(int(respjson["last_report_at"]))
    status = respjson["status"]
    collected = respjson["energy_today"]

    print(f"Energy collected today: {collected}")
    print(f"Last reported on {lastreport}")
    print(f"Solar array status is '{status}'.")

    try:
        client.admin.command("ping")
    except ConnectionFailure:
        print("Server not available")

    """try:
        for coll in client.getCollectionNames():
            print(f"default collection: {coll}")
    except ConnectionFailure:
        print("Database not available")
    """

    try:
        insert = {"LastReported": lastreport, "Collected": collected, "Status": status}
        post = collection.insert_one(insert)
        print("Created record as {0}".format(post.inserted_id))
    except pymongo.errors.ServerSelectionTimeoutError as err:
        print(err)
