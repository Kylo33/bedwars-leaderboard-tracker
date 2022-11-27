from discord import app_commands
import discord
import creds
import tabulate as tb
from tabulate import tabulate
import sqlite3
import datetime
import pytz
import os

# 1
def get_days():
    now = datetime.datetime.now(tz=pytz.timezone("US/Mountain"))
    if now.hour < 7 or (now.hour < 8 and now.minute < 30):
        yesterday = (now - datetime.timedelta(days=2)).date()
    else:
        yesterday = (now - datetime.timedelta(days=1)).date()
    days = [(yesterday - datetime.timedelta(days=day)).isoformat() for day in range(7)]
    days.reverse()
    return days


class LbTable:

    days = get_days()

    headers = [
        "#",
        "Username",
        "Wins",
        *[d.replace("2022-", "") for d in days],
        "Weekly",
    ]

    def __init__(self):
        self._data = get_data("wins_database.db")
        self.page = 0

    def next_page(self):
        if not self.page == 9:
            self.page += 1

    def prev_page(self):
        if not self.page == 0:
            self.page -= 1

    def __str__(self):
        start = self.page * 10
        end = start + 10
        table_data = []
        tb.PRESERVE_WHITESPACE = True
        for player in self._data:
            weekly = 0
            player_data = []
            player_data.extend(
                [
                    player["position"],
                    f"{player['username']:<16}",
                    f"{player['total_wins']:,}",
                ]
            )
            for d in self.days:
                if d in player["daily_wins"]:
                    player_data.append(player["daily_wins"][d])
                    weekly += player["daily_wins"][d]
                else:
                    player_data.append("-")
            player_data.append(weekly)
            table_data.append(player_data)
        return tabulate(table_data[start:end], headers=self.headers, tablefmt="simple")

    def find(self, username: str) -> None:
        position = None
        for player in self._data:
            if player["username"].lower() == username.lower():
                position = player["position"]
        if not position == None:
            self.page = int(
                f"{position - 1:02}"[0]
            )  # first digit of the position number - 1
        return self


def main():
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)
    solo_players_command(tree)
    @client.event
    async def on_ready():
        await tree.sync()
        username = str(client.user)
        print(f"Logged in as {username}")
    client.run(creds.discord_token)


def solo_players_command(tree):
    @tree.command(
        name="soloplayers",
        description="Sends information about the top 100 solo bedwars players.",
    )
    async def soloplayers(interaction):
        table = LbTable()

        class ScrollButton(discord.ui.Button):
            def __init__(self, lbl: str):
                self.lbl = lbl
                if self.lbl == "prev":
                    super().__init__(label="Prev Pg.")
                    self.disabled = True
                elif self.lbl == "next":
                    super().__init__(label="Next Pg.")

            async def callback(self, interaction):
                match self.lbl:
                    case "prev":
                        table.prev_page()
                        if table.page == 0:
                            self.disabled = True
                    case "next":
                        table.next_page()
                        if table.page == 9:
                            self.disabled = True
                if table.page == 1 or table.page == 8:
                    for btn in self.view.children:
                        btn.disabled = False
                await interaction.response.edit_message(
                    content="```" + str(table) + "```", view=self.view
                )
                self.view.timeout = 30

        class SearchModal(discord.ui.Modal):
            title = "Search for a Player"
            name = discord.ui.TextInput(label="Username")

            def __init__(self, view):
                super().__init__()
                self.view = view

            async def on_submit(self, interaction):
                table.find(self.name.value)
                if table.page == 0:
                    disable = "prev"
                elif table.page == 9:
                    disable = "next"
                else:
                    disable = None
                for btn in self.view.children:
                    btn.disabled = False
                    try:
                        if btn.lbl == disable:
                            btn.disabled = True
                    except AttributeError:
                        continue
                await interaction.response.edit_message(
                    content="```" + str(table) + "```", view=self.view
                )

        class SearchButton(discord.ui.Button):
            def __init__(self):
                super().__init__(label="Search")

            async def callback(self, interaction):
                modal = SearchModal(self.view)
                await interaction.response.send_modal(modal)

        class ScrollView(discord.ui.View):
            def __init__(self, interaction):
                super().__init__(timeout=30)
                prev_btn = ScrollButton("prev")
                next_btn = ScrollButton("next")
                self.add_item(prev_btn).add_item(next_btn).add_item(SearchButton())

            async def on_timeout(self) -> None:
                for btn in self.children:
                    btn.disabled = True
                await self.message.edit(view=self)

        view = ScrollView(interaction)
        await interaction.response.send_message(
            content="```" + str(table) + "```", view=view
        )
        view.message = await interaction.original_response()

# 2
def get_data(db: str) -> list:
    if not os.path.isfile(db): # if the database doesn't exist, return nothing
        return
    con = sqlite3.connect(db)
    cur = con.cursor()
    result = cur.execute("SELECT * FROM wins ORDER BY date, wins DESC")
    now = datetime.datetime.now(tz=pytz.timezone("US/Mountain"))
    data = []
    if now.hour < 7 or (now.hour < 8 and now.minute < 30):
        today = now.date() - datetime.timedelta(days=1)
    else:
        today = now.date()
    week_ago = today - datetime.timedelta(days=7)
    for row in result:
        entry_id, uuid, username, wins, position, date = [row[i] for i in range(6)]

        # if the data is over a week old, it is ignored.
        if datetime.date.fromisoformat(date) < week_ago:
            continue

        if uuid not in [p["uuid"] for p in data]:
            data.append({"uuid": uuid, "total_by_date": {}, "daily_wins": {}})
        for p in data:
            if date in p["total_by_date"]:
                continue
            if p["uuid"] == uuid:
                p["username"] = username
                p["position"] = position
                p["total_by_date"][date] = wins
                p["total_wins"] = wins

    for p in data:
        for day, wins in p["total_by_date"].items():
            next_day = (
                datetime.date.fromisoformat(day) + datetime.timedelta(days=1)
            ).isoformat()
            if next_day in p["total_by_date"]:
                p["daily_wins"][day] = (
                    p["total_by_date"][next_day] - p["total_by_date"][day]
                )
    latest_date = get_latest_date(data)
    data = [player for player in data if latest_date in player["total_by_date"]] # remove players who aren't on the leaderboard anymore
    return sorted(data, key=lambda r: r["position"])
# 3

def get_latest_date(data: list) -> str:
    dates = [list(player["total_by_date"].items())[-1][0] for player in data] # gets every date from the end of each player's total_by_date dict
    date_object_list = list(map(lambda d: datetime.date.fromisoformat(d), dates))
    return str(max(date_object_list))

if __name__ == "__main__":
    main()
