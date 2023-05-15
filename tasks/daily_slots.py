from datetime import *
from slots.slots_game import *
import pytz
from common import *


def daily_slots_task(client):
    async def daily_slots():
        """reset the slots and show the leaderboards for the previous day"""
        enabled = config["tasks"]["daily_slots"]["enabled"]
        if not enabled:
            return

        game = SlotsGame()
        embed, file = game.new_day()
        channel = client.get_channel(get_channel_id("dabo-table"))
        await channel.send(embed=embed, file=file)

    return {"task": daily_slots, "crontab": config["tasks"]["daily_slots"]["crontab"]}
