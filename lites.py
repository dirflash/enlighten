import RPi.GPIO as GPIO
import configparser
import time
import sys
import certifi
import pymongo
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

if __name__ == "__main__":

    start_time = time.time()

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
        print("Recycle for new data")
        GPIO.output(blue, GPIO.LOW)
        GPIO.output(green, GPIO.LOW)
        GPIO.output(red, GPIO.LOW)

        try:
            connect_time = time.time()
            info = client.server_info()
            print(
                "--- %.3f seconds to connect to MongoDB ---"
                % (time.time() - connect_time)
            )
            GPIO.output(blue, GPIO.HIGH)
        except ServerSelectionTimeoutError:
            sys.exit("--- Server not available ---")

        lastrecord = collection.find().sort("_id", -1).limit(1)
        for x in lastrecord:
            sysup = x["Reporting"]
            print(f"System reporting: {sysup}")

        if sysup is True:
            GPIO.output(green, GPIO.HIGH)
            print("System Green!")
            GPIO.output(red, GPIO.LOW)
            time.sleep(10)
        else:
            GPIO.output(red, GPIO.HIGH)
            print("System Red!")
            GPIO.output(green, GPIO.LOW)
            time.sleep(10)

        print("60 minutes to next poll")
        time.sleep(290)
        print("45 minutes to next poll")
        time.sleep(300)
        print("30 minutes to next poll")
        time.sleep(300)
        print("15 minutes to next poll")

    GPIO.cleanup()
