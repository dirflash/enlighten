#!/usr/bin/env python3
"""This script obtains collection information from Envision Solar Panels"""

__author__ = "Aaron Davis"
__version__ = "0.1.0"
__copyright__ = "Copyright (c) 2021 Aaron Davis"
__license__ = "MIT License"

import configparser
import json
import logging
from time import time, sleep
from datetime import datetime, timedelta
import requests
import certifi
import pymongo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from rich import print, box
from rich.console import Console
from rich.table import Table
from rich.logging import RichHandler
from utils.weather import weather

if __name__ == "__main__":

    start_time = time()
    FIRST_RUN = True

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
    zip_code = config["WEATHER"]["zip"]
    units = config["WEATHER"]["units"]

    MAX_MONGODB_DELAY = 500

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
        serverSelectionTimeoutMS=MAX_MONGODB_DELAY,
    )

    db = client[mongodb]
    collection = db[mongocollect]

    payload = {}
    headers = {}

    def dbprune():
        """Clean up old documents in MongoDB"""

        docs = collection.estimated_document_count()

        t = time()
        easytime = datetime.fromtimestamp(t)
        ezytime = int(easytime.timestamp())

        minus = t - 345600  # 4-days
        easytime2 = datetime.fromtimestamp(minus)
        ezytime2 = int(easytime2.timestamp())

        deldocs = collection.count_documents({"EpochLastReport": {"$lt": ezytime2}})

        before_stats_table = Table(
            title="Before Statistics", box=box.SIMPLE, style="red"
        )

        before_stats_table.add_column("Type", style="red")
        before_stats_table.add_column("Data", justify="right", style="red")

        before_stats_table.add_row("Current time", str(ezytime))
        before_stats_table.add_row("Pruning time", str(ezytime2))
        before_stats_table.add_row("Number of docs", str(docs))
        before_stats_table.add_row("Docs to delete", str(deldocs))

        if before_stats_table.columns:
            console.print(before_stats_table)
        else:
            print("[i]No data...[/i]")

        try:
            collection.delete_many({"EpochLastReport": {"$lt": ezytime2}})
        except ConnectionFailure as delerr:
            log.exception(delerr)

        newdocs = collection.estimated_document_count()
        docsdel = docs - newdocs

        after_stats_table = Table(
            title="After Statistics", box=box.SIMPLE, style="cyan"
        )

        after_stats_table.add_column("Type", style="cyan3")
        after_stats_table.add_column("Data", justify="right", style="cyan3")

        after_stats_table.add_row("Number of docs", str(newdocs))
        after_stats_table.add_row("Docs deleted", str(docsdel))

        if after_stats_table.columns:
            console.print(after_stats_table)
        else:
            print("[i]No data...[/i]")

        dbprunenext = datetime.now() + timedelta(hours=DB_PRUNE_DELAY)
        nextrundb = dbprunenext.strftime("%m-%d-%Y %H:%M:%S")
        console.log(f"--- Next db clean-up run: [bold cyan]{nextrundb}[/bold cyan] ---")

        return dbprunenext

    def format_time(time):
        """Format time to make it easier to read"""
        return time.strftime("%H").lstrip("0") + time.strftime(":%M")

    start_time = time()

    while True:

        console.log(f"--- First run is : [bold cyan]{FIRST_RUN}[/bold cyan] ---")

        if FIRST_RUN is False:
            start_time = time()

        localviz, collect = weather(api, zip_code, units)

        if localviz == "day" and collect == "sun":

            current_epoch = int(time())

            response = requests.request("GET", url, headers=headers, data=payload)
            respjson = json.loads(response.text)
            epochlastreport = respjson["last_report_at"]
            lastreport = datetime.fromtimestamp(int(respjson["last_report_at"]))
            status = respjson["status"]
            collected = respjson["energy_today"]

            lastreportdelta = (current_epoch - epochlastreport) / 60

            minutes = int(lastreportdelta)
            seconds = int((lastreportdelta * 60) % 60)

            LAST_REPORTED = str(f"{minutes:02}:{seconds:02}")

            IN_RANGE = lastreportdelta < 86400  # 24 hours

            epochdelta = current_epoch - epochlastreport

            coltable = Table(title="Solar Statistics", box=box.SIMPLE, style="cyan")

            coltable.add_column("Type", style="cyan3")
            coltable.add_column("Data", justify="right", style="cyan3")

            coltable.add_row("Last report (epoch)", str(epochlastreport))
            coltable.add_row("Current time (epoch)", str(current_epoch))
            coltable.add_row("Delta (epoch)", str(epochdelta))
            coltable.add_row("Last reported mins:secs ago", (LAST_REPORTED))
            coltable.add_row("In range? (<24 hours)", str(IN_RANGE))
            coltable.add_row("Solar array status", status)
            coltable.add_row("Energy collected", str(collected))

            if coltable.columns:
                console.print(coltable)
            else:
                print("[i]No data...[/i]")

            try:
                client.admin.command("ping")
            except ConnectionFailure as error:
                log.exception(error)

            try:
                insert = {
                    "EpochLastReport": epochlastreport,
                    "LastReport": lastreport,
                    "Collected": collected,
                    "Status": status,
                    "Reporting": IN_RANGE,
                }

                post = collection.insert_one(insert)

                if post.inserted_id == 0:
                    console.log(
                        "--- No MongoDB record created ---",
                        style="deep_pink4",
                    )
                else:
                    console.log(
                        f"--- Created MongoDB record as {0} ---".format(
                            post.inserted_id
                        ),
                        style="deep_pink4",
                    )
            except pymongo.errors.ServerSelectionTimeoutError as error:
                log.exception(error)
        else:
            console.log(
                "[bold bright_yellow] --- Waiting for sun! ---[/bold bright_yellow]"
            )

        DB_PRUNE_DELAY = 24

        if FIRST_RUN is True:
            dbprunenext = datetime.now() + timedelta(hours=DB_PRUNE_DELAY)
            nextrundb = dbprunenext.strftime("%m-%d-%Y %H:%M:%S")
            console.log(
                f"--- Next db clean-up run: [bold cyan]{nextrundb}[/bold cyan] ---"
            )

        if dbprunenext < datetime.now():
            dbprunenext = dbprune()
        else:
            countdwn = str(dbprunenext - datetime.now()).split(".", maxsplit=1)[0]
            console.log(
                f"--- Next db prune in t-minus: [bold cyan]{countdwn}[/bold cyan] ---"
            )

        RUN_DELAY = 1

        ennext = datetime.now() + timedelta(hours=RUN_DELAY)
        nextrun = ennext.strftime("%m-%d-%Y %H:%M:%S")
        console.log(f"--- Next solar data pull: [bold cyan]{nextrun}[/bold cyan] ---")

        console.log(
            f"--- Script ran in [bold cyan]{(time() - start_time):.3f} seconds[/bold cyan] ---"
        )

        FIRST_RUN = False

        console.log(
            f"--- Next poll in 1 hour: {format_time(datetime.now() + timedelta(minutes=60))} ---"
        )

        with console.status(
            "[bold green]Sleeping for 1 hour...[/]", spinner="dots12"
        ) as status:
            sleep(3600)
            console.log("[green]Finished sleeping for 1 hour[/green]")

            console.log("[bold][red]Done![/bold][/red]")
