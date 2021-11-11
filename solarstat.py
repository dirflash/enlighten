__author__ = "Aaron Davis"
__version__ = "0.1.0"
__copyright__ = "Copyright (c) 2021 Aaron Davis"
__license__ = "MIT License"

import configparser
import requests
import json
from time import time, sleep
from datetime import datetime, timedelta
import certifi
import pymongo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from rich import print, box
from rich.console import Console
from rich.table import Table
from rich.progress import track

if __name__ == "__main__":

    start_time = time()
    first = True

    console = Console()

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
        if first is False:
            start_time = time()

        console.log(f"--- First run is : [bold cyan]{first}[/bold cyan] ---")

        current_epoch = int(time())

        response = requests.request("GET", url, headers=headers, data=payload)
        respjson = json.loads(response.text)
        epochlastreport = respjson["last_report_at"]
        lastreport = datetime.fromtimestamp(int(respjson["last_report_at"]))
        status = respjson["status"]
        collected = respjson["energy_today"]

        lastreportdelta = (current_epoch - epochlastreport) / 60
        hours = int(lastreportdelta)
        minutes = (lastreportdelta * 60) % 60
        seconds = (lastreportdelta * 3600) % 60
        lrd = str(("%d:%02d.%02d" % (hours, minutes, seconds)))

        if lastreportdelta < 86400:
            inrange = True
        else:
            inrange = False

        epochdelta = current_epoch - epochlastreport

        coltable = Table(title="Solar Statistics", box=box.SIMPLE, style="cyan")

        coltable.add_column("Type", style="cyan3")
        coltable.add_column("Data", justify="right", style="cyan3")

        coltable.add_row("Last report (epoch)", str(epochlastreport))
        coltable.add_row("Current time (epoch)", str(current_epoch))
        coltable.add_row("Delta (epoch)", str(epochdelta))
        coltable.add_row("Last reported hrs:mins:secs ago", (lrd))
        coltable.add_row("In range?", str(inrange))
        coltable.add_row("Solar array status", status)
        coltable.add_row("Energy collected", str(collected))

        if coltable.columns:
            console.print(coltable)
        else:
            print("[i]No data...[/i]")

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
                "Reporting": inrange,
            }
            post = collection.insert_one(insert)
            console.log(
                "--- Created MongoDB record as {0} ---".format(post.inserted_id),
                style="deep_pink4",
            )
        except pymongo.errors.ServerSelectionTimeoutError as err:
            print(err)

        console.log(
            "--- Script ran in [bold cyan]%.3f seconds[/bold cyan] ---"
            % (time() - start_time)
        )

        ennext = datetime.now() + timedelta(seconds=14400)
        nextrun = ennext.strftime("%m-%d-%Y %H:%M:%S")
        console.log(f"--- Next run: [bold cyan]{nextrun}[/bold cyan] ---")

        first = False

        for t in range(1, 4):
            print(f"Count down {t}.")
            for n in track(range(3600), description="Count down", refresh_per_second=2):
                sleep(1)
