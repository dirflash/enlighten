#!/usr/bin/env python3
"""This script collects weather details"""

__author__ = "Aaron Davis"
__version__ = "0.1.0"
__copyright__ = "Copyright (c) 2021 Aaron Davis"
__license__ = "MIT License"

from time import time, sleep
import configparser
import sys
import os
import requests
from requests.exceptions import Timeout
from requests.exceptions import ConnectionError  # pylint: disable=redefined-builtin
from rich import print, box  # pylint: disable=redefined-builtin
from rich.table import Table
from rich.console import Console

console = Console()


def retrieve_weather(url):
    """Request weather information"""
    timeout = False
    try:
        response = requests.get(url, timeout=1)
        status_code = response.status_code
        response.raise_for_status()
    except Timeout:
        print(
            f"[red bold]The 'get weather' request timed out with status code {status_code}![/]"
        )
        response = "error"
        status_code = 0
        timeout = True
    except ConnectionError as connect_error:
        print(f"[red bold]Error: [/] {connect_error}")
        response = "error"
        status_code = 0
        timeout = True
    except requests.HTTPError:
        status = response.status_code
        if status == 401:
            print("[orange1]Invalid API key.[/]")
            sys.exit(1)
        elif status == 404:
            print("[orange1]Invalid input.[/]")
            sys.exit(1)
        elif status in (429, 443):
            print("[orange1]API calls per minute exceeded.[/]")
            response = "error"
            status_code = 0
            timeout = True
    return (response, status_code, timeout)


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

    response, status_code, timeout = retrieve_weather(url)

    while timeout is True:
        with console.status(
            "[bold green]Sleeping for 30 minutes...[/]", spinner="dots12"
        ) as status:
            sleep(1800)
            console.log("[green]Finished sleeping. Try again.[/green]")
        response = retrieve_weather(url)

    if timeout is False:
        if status_code == 200:
            data = response.json()
            weather_id = data["weather"][0]["id"]
            sunrise = data["sys"]["sunrise"]
            sunset = data["sys"]["sunset"]
        else:
            weather_id = 804
            sunrise = time() - (time() - 60)
            sunset = time() + (time() + 60)

        localtime = time()

        if sunset > localtime > sunrise:
            localviz = "day"

            if weather_id == 800:
                collect = "sun"
            elif 804 > weather_id > 800:
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

        coltable.add_row("Status Code", str(status_code))
        coltable.add_row("Local Visibility", str(localviz))
        coltable.add_row("Collectibility", collect_msg)

        if coltable.columns:
            console.print(coltable)
        else:
            print("[i]No data...[/i]")

        return (localviz, collect)


if __name__ == "__main__":
    config_file = os.path.abspath(r"c:\code\enlighten\enlighten\config.ini")
    config = configparser.ConfigParser()
    config.read(config_file)
    api = config["WEATHER"]["weather_api"]
    zip_code = config["WEATHER"]["zip"]
    units = config["WEATHER"]["units"]
    localviz, collect = weather(api, zip_code, units)
