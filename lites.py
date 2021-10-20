__author__ = "Aaron Davis"
__version__ = "0.1.0"
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

if __name__ == "__main__":

    start_time = time()

    console = Console()

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    blue = 17
    red = 23
    green = 25

    GPIO.setup(blue, GPIO.OUT)
    GPIO.setup(red, GPIO.OUT)
    GPIO.setup(green, GPIO.OUT)

    config = configparser.ConfigParser()
    config.read("config.ini")
    mongoaddr = config["MONGO"]["mongo_addr"]
    mongodb = config["MONGO"]["mongo_db"]
    mongocollect = config["MONGO"]["mongo_collect"]
    mongouser = config["MONGO"]["user_name"]
    mongopw = config["MONGO"]["password"]

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

        try:
            startime = datetime.now()
            info = client.server_info()
            pconnect_time = ((str(datetime.now() - startime))[:-4]).replace("0:00:", "")
            # qconnect_time = pconnect_time.replace("0:00:", "")
            connect_time = "".join(pconnect_time)

            GPIO.output(blue, GPIO.HIGH)
        except ServerSelectionTimeoutError:
            sys.exit("--- Server not available ---")

        lastrecord = collection.find().sort("_id", -1).limit(1)
        for x in lastrecord:
            sysup = x["Reporting"]
            # print(f"System reporting: {sysup}")

        coltable = Table(title="Solar DB Statistics", box=box.SIMPLE, style="cyan")

        coltable.add_column("Type", style="cyan3")
        coltable.add_column("Data", justify="right", style="cyan3")

        coltable.add_row("Seconds to connect to DB", str(connect_time))
        coltable.add_row("Current reporting", str(sysup))

        if coltable.columns:
            console.print(coltable)
        else:
            console.log("[i]--- No data... ---[/i]")

        if sysup is True:
            GPIO.output(green, GPIO.HIGH)
            console.log("[bold green] --- System Green! ---[/bold green]")
            GPIO.output(red, GPIO.LOW)
            sleep(10)
        else:
            GPIO.output(red, GPIO.HIGH)
            console.log("[bold red]--- System Red! ----[/bold red]")
            GPIO.output(green, GPIO.LOW)
            sleep(10)

        instant = datetime.now()
        nextpoll = instant + timedelta(minutes=60)
        instup = instant.timetuple()

        now = datetime.now()

        def format(time):
            return time.strftime("%H").lstrip("0") + time.strftime(":%M")

        console.log(f"Next poll in 1 hour: {format(now + timedelta(minutes=60))}")

        # quit()

        # pollhours = nextpoll
        # pollminutes = (nextpoll * 60) % 60
        # pollseconds = (nextpoll * 3600) % 60
        # polltime = str(("%d:%02d.%02d" % (pollhours, pollminutes, pollseconds)))

        # coltable.add_row("Next polling time", (polltime))

        # print(f"Next poll at {polltime}")
        # for n in track(range(3590), description="Waiting..."):
        # time.sleep(60)

        console.log("[medium_orchid3]sleeping...[/medium_orchid3]")
        sleep(1190)
        console.log("45 minutes to next poll")
        sleep(1200)
        console.log("30 minutes to next poll")
        sleep(1200)
        console.log("15 minutes to next poll")

    GPIO.cleanup()
