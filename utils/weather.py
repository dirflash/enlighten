#!/usr/bin/env python3
"""This script collects weather details"""

__author__ = "Aaron Davis"
__version__ = "0.1.0"
__copyright__ = "Copyright (c) 2021 Aaron Davis"
__license__ = "MIT License"

from time import time
import sys
import requests
from rich import print, box
from rich.table import Table
from rich.console import Console

console = Console()


def weather(api, zip_code, units):
    """Get weather details"""

    url = (
        "http://api.openweathermap.org/data/2.5/weather?"
        + "zip="
        + zip_code
        + "&appid="
        + api
        + "&units="
        + units
    )

    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.HTTPError:
        status = response.status_code
        if status == 401:
            print("[orange1]Invalid API key.[/]")
        elif status == 404:
            print("[orange1]Invalid input.[/]")
        elif status in (429, 443):
            print("[orange1]API calls per minute exceeded.[/]")
        sys.exit(1)

    data = response.json()

    weather_id = data["weather"][0]["id"]
    sunrise = data["sys"]["sunrise"]
    sunset = data["sys"]["sunset"]

    localtime = time()

    if sunrise > localtime > sunset:
        localviz = "day"

        if weather_id == 800:
            collect = "sun"
        elif weather_id > 800 and weather_id < 804:
            collect = "sun"
        else:
            collect = "no sun"

    else:
        localviz = "night"
        collect = "no sun"

    collect_msg = collect + " (" + str(weather_id) + ")"

    coltable = Table(title="Weather Statistics", box=box.SIMPLE, style="cyan")

    coltable.add_column("Type", style="cyan3")
    coltable.add_column("Data", justify="right", style="cyan3")

    coltable.add_row("Local Visibility", str(localviz))
    coltable.add_row("Collectibility", collect_msg)

    if coltable.columns:
        console.print(coltable)
    else:
        print("[i]No data...[/i]")

    return (localviz, collect)
