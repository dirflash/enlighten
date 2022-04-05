#!/usr/bin/env python3
"""This script collects weather details"""

__author__ = "Aaron Davis"
__version__ = "0.1.0"
__copyright__ = "Copyright (c) 2022 Aaron Davis"
__license__ = "MIT License"

from time import time
from datetime import timedelta
import configparser
import os
import requests
from requests.adapters import HTTPAdapter, Retry
from requests.exceptions import Timeout
from rich import print, box  # pylint: disable=redefined-builtin
from rich.table import Table
from rich.console import Console

console = Console()


def retrieve_weather(url):
    """Request weather information"""
    timeout = False
    try:
        retries = Retry(total=3, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        http = requests.Session()
        http.mount("http://", adapter)
        response = http.get(url, timeout=5)
        status_code = response.status_code
        response_time = response.elapsed
        if response_time > timedelta(seconds=0.6):
            console.log(
                f"[bright_yellow]Response time to Open Weather API: {response_time}[/]"
            )
        else:
            console.log(f"[green]Response time to Open Weather API: {response_time}[/]")

    except Timeout:
        print("[red bold]The 'get weather' request timed out![/]")
        response = "error"
        status_code = 0
        timeout = True
    return (response, status_code, timeout)


def weather(api, zip_code, units):
    """Get weather details"""
    console.log("[green]Entered weather function.[/]")

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

        console.log("[green]Exiting weather function.[/]")

        return (localviz, collect)


if __name__ == "__main__":
    config_file = os.path.abspath(r"c:\code\enlighten\enlighten\config.ini")
    config = configparser.ConfigParser()
    config.read(config_file)
    api = config["WEATHER"]["weather_api"]
    zip_code = config["WEATHER"]["zip"]
    units = config["WEATHER"]["units"]
    localviz, collect = weather(api, zip_code, units)
