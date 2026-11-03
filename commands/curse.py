import json
import random

import discord

from common.config_utils import config
from common.discord_bot import bot

command_config = config["commands"]["curse"]

# Load JSON Data
f = open(command_config["data"])
curse_data = json.load(f)
f.close()

@bot.slash_command(
  name="curse",
  description="Small Curses for a Kind Heart (apers' Curse Service)"
)
async def curse(ctx:discord.ApplicationContext):
  selected_curse = random.choice(curse_data['curses'])
  embed = discord.Embed(
    description=f"> {selected_curse}",
    color=discord.Color.magenta()
  )
  await ctx.respond(embed=embed)
