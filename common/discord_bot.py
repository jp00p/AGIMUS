# __________        __
# \______   \ _____/  |_
#  |    |  _//  _ \   __\
#  |    |   (  <_> )  |
#  |______  /\____/|__|
#         \/
import discord
from discord.ext import commands

from common.config_utils import config

intents = discord.Intents.all()
bot = commands.Bot(
    intents=intents,
    test_guilds=config["guild_ids"],
    auto_sync_commands=True,
    command_prefix="!"
)
