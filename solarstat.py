__author__ = "Aaron Davis"
__version__ = "0.1.0"
__copyright__ = "Copyright (c) 2021 Aaron Davis"
__license__ = "MIT License"

import configparser
import requests
import json
import logging
from time import time, sleep
from datetime import datetime, timedelta
import certifi
import pymongo
import sys
from utils import weather
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from rich import print, box
from rich.console import Console
from rich.table import Table
from rich.progress import track
from rich.logging import RichHandler
from utils.weather import weather

if __name__ == "__main__":

    start_time = time()
    first = True

    console = Console()

    FORMAT = "%(message)s"
    logging.basicConfig(
        level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
    )

    logging.basicConfig(
        level="NOTSET",
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )

    log = logging.getLogger("rich")

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
    api = config["WEATHER"]["weather_api"]
    zip = config["WEATHER"]["zip"]
    units = config["WEATHER"]["units"]

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

    def dbprune():
        docs = collection.estimated_document_count()

        t = time()
        easytime = datetime.fromtimestamp(t)
        ezytime = int(easytime.timestamp())

        minus = t - 345600  # 4-days
        easytime2 = datetime.fromtimestamp(minus)
        ezytime2 = int(easytime2.timestamp())

        deldocs = collection.count_documents({"EpochLastReport": {"$lt": ezytime2}})

        coltable = Table(title="Before Statistics", box=box.SIMPLE, style="red")

        coltable.add_column("Type", style="red")
        coltable.add_column("Data", justify="right", style="red")

        coltable.add_row("Current time", str(ezytime))
        coltable.add_row("Pruning time", str(ezytime2))
        coltable.add_row("Number of docs", str(docs))
        coltable.add_row("Docs to delete", str(deldocs))

        if coltable.columns:
            console.print(coltable)
        else:
            print("[i]No data...[/i]")

        delold = collection.delete_many({"EpochLastReport": {"$lt": ezytime2}})

        newdocs = collection.estimated_document_count()
        docsdel = docs - newdocs

        coltable = Table(title="After Statistics", box=box.SIMPLE, style="cyan")

        coltable.add_column("Type", style="cyan3")
        coltable.add_column("Data", justify="right", style="cyan3")

        coltable.add_row("Number of docs", str(newdocs))
        coltable.add_row("Docs deleted", str(docsdel))

        if coltable.columns:
            console.print(coltable)
        else:
            print("[i]No data...[/i]")

        dbprunenext = datetime.now() + timedelta(hours=dbprunedelay)
        nextrundb = dbprunenext.strftime("%m-%d-%Y %H:%M:%S")
        console.log(f"--- Next db clean-up run: [bold cyan]{nextrundb}[/bold cyan] ---")

        return dbprunenext

    while True:

        # localviz, collect = weather()
        localviz, collect = weather(api, zip, units)

        if localviz == "day" and collect == "sun":

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
            except ConnectionFailure as err:
                log.exception(err)

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
                log.exception(err)

            dbprunedelay = 24

            if first is True:
                dbprunenext = datetime.now() + timedelta(hours=dbprunedelay)
                nextrundb = dbprunenext.strftime("%m-%d-%Y %H:%M:%S")
                console.log(
                    f"--- Next db clean-up run: [bold cyan]{nextrundb}[/bold cyan] ---"
                )

            if dbprunenext < datetime.now():
                dbprunenext = dbprune()
            else:
                countdwn = dbprunenext - datetime.now()
                console.log(
                    f"--- Next db prune in t-minus: [bold cyan]{countdwn}[/bold cyan] ---"
                )

            rundelay = 4

            ennext = datetime.now() + timedelta(hours=rundelay)
            nextrun = ennext.strftime("%m-%d-%Y %H:%M:%S")
            console.log(
                f"--- Next solar data pull: [bold cyan]{nextrun}[/bold cyan] ---"
            )

            console.log(
                "--- Script ran in [bold cyan]%.3f seconds[/bold cyan] ---"
                % (time() - start_time)
            )

            first = False

        for t in range(1, 4):
            with console.status(
                "[bold green]Sleeping for 1 hour...", spinner="dots12"
            ) as status:
                sleep(3600)
                console.log(f"[green]Finished sleeping for [/green] {t} hour")

                console.log(f"[bold][red]Done!")
