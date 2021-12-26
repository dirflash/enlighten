#!/usr/bin/env python3
"""
This script retrieves Envision Solar Panels from MongoDB and triggers LED's depending on the status
"""

__author__ = "Aaron Davis"
__version__ = "0.2.0"
__copyright__ = "Copyright (c) 2021 Aaron Davis"
__license__ = "MIT License"

import configparser
from datetime import datetime, timedelta
from time import time, sleep
import sys
from RPi import GPIO
import certifi
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from rich import box
from rich.console import Console
from rich.table import Table
from utils.weather import weather


def format_time(in_time):
    """Formats time to make it easier to read."""
    return in_time.strftime("%H").lstrip("0") + in_time.strftime(":%M")


if __name__ == "__main__":

    start_time = time()
    FIRST_RUN = True

    console = Console()

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    BLUE = 17
    RED = 23
    GREEN = 25
    WHITE = 12
    YELLOW = 20

    GPIO.setup(BLUE, GPIO.OUT)
    GPIO.setup(RED, GPIO.OUT)
    GPIO.setup(GREEN, GPIO.OUT)
    GPIO.setup(WHITE, GPIO.OUT)
    GPIO.setup(YELLOW, GPIO.OUT)

    CONFIG_FILE = "./config.ini"

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    mongoaddr = config["MONGO"]["mongo_addr"]
    mongodb = config["MONGO"]["mongo_db"]
    mongocollect = config["MONGO"]["mongo_collect"]
    mongouser = config["MONGO"]["user_name"]
    mongopw = config["MONGO"]["password"]
    api = config["WEATHER"]["weather_api"]
    zip_code = config["WEATHER"]["zip"]
    units = config["WEATHER"]["units"]

    MAX_MONGODB_DELAY = 30000

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

    while True:

        console.log(f"--- First run is : [bold cyan]{FIRST_RUN}[/bold cyan] ---")

        if FIRST_RUN is False:
            start_time = time()

        console.log("[bold green]--- Recycle for new data ---[/bold green]")
        now = datetime.now().strftime("%m-%d-%Y %I:%M:%S %p")
        console.log(f"--- Current time: {now} ---")
        GPIO.output(BLUE, GPIO.LOW)
        GPIO.output(GREEN, GPIO.LOW)
        GPIO.output(RED, GPIO.LOW)
        GPIO.output(WHITE, GPIO.LOW)
        GPIO.output(YELLOW, GPIO.LOW)
        console.log("[bold bright_yellow]--- LED's off! ----[/bold bright_yellow]")

        localviz, collect = weather(api, zip_code, units)

        if localviz == "day" and collect == "sun":
            GPIO.output(WHITE, GPIO.HIGH)
            try:
                startime = time()
                info = client.server_info()
                POST_CONNECT = time() - startime
                connect_seconds = int(POST_CONNECT)
                connect_milli = int((POST_CONNECT * 60) % 60)
                CONNECT_TIME = str(f"{connect_seconds:02}.{connect_milli:02}")
                GPIO.output(BLUE, GPIO.HIGH)
            except ServerSelectionTimeoutError:
                sys.exit("--- Server not available ---")

            lastrecord = collection.find().sort("_id", -1).limit(1)
            for x in lastrecord:
                sysup = x["Reporting"]
                collected = x["Collected"]
                lastreport = x["EpochLastReport"]

            lrd = time() - lastreport
            REPORTED_DIFF = str(timedelta(seconds=lrd)).split(".", maxsplit=1)[0]

            db_stats_table = Table(
                title="Solar DB Statistics", box=box.SIMPLE, style="cyan"
            )

            db_stats_table.add_column("Type", style="cyan3")
            db_stats_table.add_column("Data", justify="right", style="cyan3")

            db_stats_table.add_row("Seconds to connect to DB", CONNECT_TIME)
            db_stats_table.add_row("Reporting", str(sysup))
            db_stats_table.add_row("Energy collected", str(collected))
            db_stats_table.add_row("Since last report", str(REPORTED_DIFF))

            if db_stats_table.columns:
                console.print(db_stats_table)
            else:
                console.log("[i]--- No data... ---[/i]")

            if sysup is True:
                GPIO.output(GREEN, GPIO.HIGH)
                console.log(f"[bold green]--- Green LED on! ---[/bold green]")
                console.log("[bold green]--- System Up! ---[/bold green]")
                sleep(10)
            else:
                GPIO.output(RED, GPIO.HIGH)
                console.log("[bold red]--- Red LED on! ----[/bold red]")
                console.log("[bold red]--- System Down! ----[/bold red]")
                sleep(10)

            if lrd > 86400:
                GPIO.output(RED, GPIO.HIGH)
                console.log("[bold red]--- Red LED on! ----[/bold red]")
                console.log("[bold red]--- System Reporting Delay! ---[/bold red]")
            else:
                GPIO.output(WHITE, GPIO.HIGH)
                console.log("[bold white]--- White LED on! ----[/bold white]")
                console.log("[bold white]--- System Reporting Timely! ---[/bold white]")
        else:
            GPIO.output(YELLOW, GPIO.HIGH)
            console.log(
                "[bold bright_yellow]--- Waiting for sun! ---[/bold bright_yellow]"
            )
            console.log("[bright_yellow]--- Yellow LED on! ----[/bright_yellow]")

        instant = datetime.now()
        nextpoll = instant + timedelta(minutes=60)
        instup = instant.timetuple()

        now = datetime.now()

        console.log(
            f"--- Script ran in [bold cyan]{(time() - start_time):.3f}[/bold cyan] seconds ---"
        )

        FIRST_RUN = False

        console.log(
            f"Next poll in 30 minutes: {format_time(now + timedelta(minutes=30))}"
        )

        with console.status(
            "[bold green]Sleeping for 30 minutes...", spinner="dots12"
        ) as status:
            sleep(1800)
            console.log(
                "[green]Finished sleeping for [/green] 30 [green]minutes[/green]"
            )

            console.log("[bold][red]Done![/]")

    GPIO.cleanup()
