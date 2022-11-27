import requests
from bs4 import BeautifulSoup
import re
import aiohttp
import creds
import asyncio
import sqlite3
import datetime
import schedule
import time
import pytz


def main():
    insert_db()
    # figure out what time 7:30 mst is in the local timezone of the server
    local_tz = datetime.datetime.utcnow().astimezone().tzinfo
    today = datetime.date.today()
    mst_reset_time = datetime.datetime(
        today.year, today.month, today.day, 7, 30, tzinfo=pytz.timezone("US/Mountain")
    ).astimezone(local_tz)
    schedule.every().day.at(
        f"{mst_reset_time.hour:02}:{mst_reset_time.minute:02}:00"
    ).do(insert_db)
    while True:
        schedule.run_pending()
        time.sleep(1)


def get_usernames_uuids(): # grabs the top 100 players and their uuids
    all_players = []
    sp = get_source("https://hypixel.net/bedwars/leaderboard/solo")
    for position, player in enumerate(sp.find_all(is_player_tag)):
        username = player.find("a").text.strip()
        uuid = re.search(
            r"/([a-z0-9]{32})",
            player.find("img", src=re.compile("crafatar.com"))["src"],
        ).group(1)
        all_players.append({"username": username, "uuid": uuid})
    return all_players


def is_player_tag(tag):
    return tag.name == "tr" and tag.has_key("class") and not tag["class"]


def get_source(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:106.0) Gecko/20100101 Firefox/106.0"
    }
    lb_page = requests.get(url, headers=headers).text
    return BeautifulSoup(lb_page, "html.parser")


async def single_player_wins(uuid: str) -> int:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://api.hypixel.net/player",
            params={"uuid": uuid, "key": creds.hypixel_api_key},
        ) as response:
            json_resp = await response.json()
            return json_resp["player"]["stats"]["Bedwars"]["eight_one_wins_bedwars"]


async def get_full_dict(): # more accurate than scraping wins from website
    player_dict = get_usernames_uuids()
    coroutines = [single_player_wins(item["uuid"]) for item in player_dict]

    wins_list = await asyncio.gather(*coroutines)
    for pos, user in enumerate(player_dict):
        user["wins"] = wins_list[pos]
        user["position"] = pos + 1
    return player_dict


def insert_db():
    sql_connection = sqlite3.connect("wins_database.db")

    cursor = sql_connection.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS wins(entry_id INTEGER PRIMARY KEY AUTOINCREMENT, uuid TEXT, username TEXT, wins INTEGER, position INTEGER, date DATE)"
    )

    full_dict = [
        dict(**player, date=datetime.date.today().isoformat())
        for player in asyncio.run(get_full_dict())
    ]

    cursor.executemany(
        "INSERT INTO wins (uuid, username, wins, position, date) VALUES(:uuid, :username, :wins, :position, :date)",
        full_dict,
    )

    sql_connection.commit()
    print(f"db was updated")


if __name__ == "__main__":
    main()
