__author__ = "Aaron Davis"
__version__ = "0.2.0"
__copyright__ = "Copyright (c) 2021 Aaron Davis"
__license__ = "MIT License"

import RPi.GPIO as GPIO
import configparser
from datetime import datetime, timedelta
from time import time, sleep, strftime, ctime
import sys
import certifi
import pymongo
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from rich import print, box
from rich.console import Console
from rich.table import Table
from rich.progress import track
from utils.weather import weather

if __name__ == "__main__":

    start_time = time()

    console = Console()

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    blue = 17
    red = 23
    green = 25
    white = 12

    GPIO.setup(blue, GPIO.OUT)
    GPIO.setup(red, GPIO.OUT)
    GPIO.setup(green, GPIO.OUT)
    GPIO.setup(white, GPIO.OUT)

    config_file = "./config.ini"

    config = configparser.ConfigParser()
    config.read(config_file)
    mongoaddr = config["MONGO"]["mongo_addr"]
    mongodb = config["MONGO"]["mongo_db"]
    mongocollect = config["MONGO"]["mongo_collect"]
    mongouser = config["MONGO"]["user_name"]
    mongopw = config["MONGO"]["password"]
    api = config["WEATHER"]["weather_api"]
    zip = config["WEATHER"]["zip"]
    units = config["WEATHER"]["units"]

    maxMongoDBDelay = 30000

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

    while True:
        console.log("[bold green]--- Recycle for new data ---[/bold green]")
        now = datetime.now().strftime("%m-%d-%Y %I:%M:%S")
        console.log(f"--- Current time: {now} ---")
        GPIO.output(blue, GPIO.LOW)
        GPIO.output(green, GPIO.LOW)
        GPIO.output(red, GPIO.LOW)
        GPIO.output(white, GPIO.LOW)

        try:
            startime = datetime.now()
            info = client.server_info()
            pconnect_time = ((str(datetime.now() - startime))[:-4]).replace("0:00:", "")
            connect_time = "".join(pconnect_time)

            GPIO.output(blue, GPIO.HIGH)
        except ServerSelectionTimeoutError:
            sys.exit("--- Server not available ---")

        lastrecord = collection.find().sort("_id", -1).limit(1)
        for x in lastrecord:
            sysup = x["Reporting"]
            collected = x["Collected"]
            lastreport = x["EpochLastReport"]

        lrd = (int(time()) - lastreport) / 60
        lrmins = int(lrd)
        lrsecs = (lrd * 60) % 60
        reporteddiff = str(("%02d:%02d" % (lrmins, lrsecs)))

        coltable = Table(title="Solar DB Statistics", box=box.SIMPLE, style="cyan")

        coltable.add_column("Type", style="cyan3")
        coltable.add_column("Data", justify="right", style="cyan3")

        coltable.add_row("Seconds to connect to DB", str(connect_time))
        coltable.add_row("Current reporting", str(sysup))
        coltable.add_row("Energy collected", str(collected))
        coltable.add_row("Since last report (mmm:ss)", str(reporteddiff))

        if coltable.columns:
            console.print(coltable)
        else:
            console.log("[i]--- No data... ---[/i]")

        if sysup is True:
            GPIO.output(green, GPIO.HIGH)
            console.log("[bold green] --- System Green! ---[/bold green]")
            GPIO.output(red, GPIO.LOW)
            GPIO.output(white, GPIO.LOW)
            sleep(10)
        else:
            GPIO.output(red, GPIO.HIGH)
            console.log("[bold red]--- System Red! ----[/bold red]")
            GPIO.output(green, GPIO.LOW)
            GPIO.output(white, GPIO.LOW)
            sleep(10)

        if lrd > 86400:
            GPIO.output(green, GPIO.LOW)
            GPIO.output(red, GPIO.LOW)
            GPIO.output(white, GPIO.HIGH)
            console.log(
                "[bold bright_yellow] --- System Reporting Delay! ---[/bold bright_yellow]"
            )
        else:
            GPIO.output(white, GPIO.LOW)
            console.log(
                "[bold bright_yellow] --- System Reporting Timely! ---[/bold bright_yellow]"
            )

        localviz, collect = weather(api, zip, units)

        if localviz == "day" and collect == "sun":
            GPIO.output(white, GPIO.HIGH)
        else:
            GPIO.output(white, GPIO.LOW)

        instant = datetime.now()
        nextpoll = instant + timedelta(minutes=60)
        instup = instant.timetuple()

        now = datetime.now()

        def format(time):
            return time.strftime("%H").lstrip("0") + time.strftime(":%M")

        console.log(f"Next poll in 2 hours: {format(now + timedelta(minutes=120))}")

        for t in range(1, 2):
            with console.status(
                "[bold green]Sleeping for 1 hour...", spinner="dots12"
            ) as status:
                sleep(3600)
                console.log(f"[green]Finished sleeping for [/green] {t} hour")

                console.log(f"[bold][red]Done!")

    GPIO.cleanup()
