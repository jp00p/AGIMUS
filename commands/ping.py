from common import *
from utils.check_channel_access import access_check

# ping() - Entrypoint for !ping command
# ctx[required]: discord.Context
# This function is the main entrypoint of the !ping command
# and will return the client's latency value in milliseconds
@bot.command()
@commands.check(access_check)
async def ping(ctx):
  logger.info(f"{Fore.LIGHTYELLOW_EX}{Style.BRIGHT}Ping pong!{Style.RESET_ALL}{Fore.RESET}")
  await ctx.send("Pong! {}ms".format(round(bot.latency * 1000)))
  