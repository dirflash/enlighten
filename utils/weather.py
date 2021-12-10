import json
import requests
import configparser
import sys
from rich import print, box
from rich.table import Table
from rich.console import Console
from time import time

console = Console()


def weather(api, zip, units):

    url = (
        "http://api.openweathermap.org/data/2.5/weather?"
        + "zip="
        + zip
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

    if localtime > sunrise and localtime < sunset:
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

    coltable = Table(title="Weather Statistics", box=box.SIMPLE, style="cyan")

    coltable.add_column("Type", style="cyan3")
    coltable.add_column("Data", justify="right", style="cyan3")

    coltable.add_row("Local Visibility", str(localviz))
    coltable.add_row("Collectibility", str(collect))

    if coltable.columns:
        console.print(coltable)
    else:
        print("[i]No data...[/i]")

    return (localviz, collect)


if __name__ == "__main__":
    weather(api, zip, units)
