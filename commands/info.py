import re
from os.path import exists

from common import *
from utils.check_channel_access import access_check
from utils.show_utils import get_show_embed

command_config = config["commands"]["info"]

# Load JSON Data
f = open(command_config["data"])
info_data = json.load(f)
f.close()

# Set up option choices
show_choices = []
show_keys = sorted(list(info_data.keys()), key=lambda k: info_data[k]['name'])
for show_key in show_keys:
  show_data = info_data[show_key]
  if show_data["enabled"]:
    show_choice = discord.OptionChoice(
      name=show_data["name"],
      value=show_key
    )
    show_choices.append(show_choice)

# info() - Entrypoint for /info command
# This function is the main entrypoint of the /info command
@bot.slash_command(
  name="info",
  description="Get information about episodes of a show"
)
@option(
  name="show",
  description="Which show?",
  required=True,
  choices=show_choices
)
@option(
  name="episode",
  description="Season and Episode Number in sXXeXX format.",
  required=True
)
@commands.check(access_check)
async def info(ctx:discord.ApplicationContext, show:str, episode:str):
  try:
    logger.info(f"{Fore.CYAN}Firing /info command!{Fore.RESET}")
    if not bool(re.search(r'^s\d\de\d\d$', episode, re.IGNORECASE)):
      await ctx.respond(
        embed=discord.Embed(
          title="Invalid Episode Format!",
          description="Please use the format 'sXXeXX'",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    found = False
    if exists(f"./data/episodes/{show}.json"):
      f = open(f"./data/episodes/{show}.json")
      show_data = json.load(f)
      f.close()
      season_no = re.sub(r'e.*', '', episode, re.IGNORECASE).replace("s","").zfill(2)
      episode_no = re.sub(r'.*e', '', episode, re.IGNORECASE).zfill(2)
      logger.info(f"{Fore.LIGHTCYAN_EX}{show} s{season_no}e{episode_no}{Fore.RESET}")
      episode_index = -1
      for ep in show_data["episodes"]:
        episode_index = episode_index + 1
        if ep["season"] == season_no and ep["episode"] == episode_no:
          found = True
          break
    if found:
      display_embed = get_show_embed(show_data, episode_index, show)
      await ctx.respond(embed=display_embed)
    else:
      await ctx.respond("Could not find this episode.\n" \
        + "If this episode should exist, or is incorrect, help fix the source data here:\n" \
        + "https://github.com/jp00p/FoDBot-SQL/tree/main/data/episodes",
        ephemeral=True
      )
  except BaseException as e:
    logger.info(f">>> ERROR: {e}")
