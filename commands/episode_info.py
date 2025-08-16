import json
import re
from os.path import exists

import discord
from colorama import Fore
from discord.ext import commands

from common import config, bot, logger
from utils.check_channel_access import access_check
from utils.show_utils import get_show_embed
from utils.string_utils import strip_bullshit

command_config = config["commands"]["episode_info"]

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

season_and_episode = re.compile(r"s\s*(\d+)\s*e\s*(\d+)", re.IGNORECASE)

async def title_autocomplete(ctx: discord.AutocompleteContext):
  show = ctx.options['show']
  if exists(f"./data/episodes/{show}.json"):
    f = open(f"./data/episodes/{show}.json")
    show_data = json.load(f)
    f.close()
    episode_titles = [e['title'] for e in show_data["episodes"]]

    results = []
    for t in episode_titles:
      if strip_bullshit(ctx.value.lower()) in strip_bullshit(t.lower()):
        results.append(t)
    return results
  else:
    return ['Invalid Show!']

@bot.slash_command(
  name="episode_info",
  description="Get information about episodes of a show"
)
@discord.option(
  name="show",
  description="Which show?",
  required=True,
  choices=show_choices
)
@discord.option(
  name="episode_title",
  description="Episode Title (Search) or Number",
  required=True,
  autocomplete=title_autocomplete
)
@commands.check(access_check)
async def episode_info(ctx:discord.ApplicationContext, show:str, episode_title:str):
  """
  This function is the main entrypoint of the /info command
  """
  try:
    logger.info(f"{Fore.CYAN}Firing /episode_info command!{Fore.RESET}")

    if not exists(f"./data/episodes/{show}.json"):
      await ctx.respond(
        embed=discord.Embed(
          title="Invalid Show!",
          description="If this show should exist, or is incorrect, help fix the source data here:\n"
                      "https://github.com/jp00p/AGIMUS/tree/main/data/episodes"
        ),
        ephemeral=True
      )
      return

    with open(f"./data/episodes/{show}.json") as f:
      show_data = json.load(f)

    episode_number_match = season_and_episode.match(episode_title)
    if episode_number_match:
      season_num = episode_number_match[1]
      if len(season_num) == 1:
        season_num = f"0{season_num}"
      episode_num = episode_number_match[2]
      if len(episode_num) == 1:
        episode_num = f"0{episode_num}"
      for episode_index, episode_data in enumerate(show_data["episodes"]):
        if episode_data["season"] == season_num and episode_data["episode"] == episode_num:
          display_embed = get_show_embed(show_data, episode_index, show)
          await ctx.respond(embed=display_embed)
          return
      
    episode_titles = [e['title'] for e in show_data["episodes"]]
    if episode_title in episode_titles:
      episode_index = episode_titles.index(episode_title)
      display_embed = get_show_embed(show_data, episode_index, show)
      await ctx.respond(embed=display_embed)
    else:
      await ctx.respond(
        embed=discord.Embed(
          title="Invalid Episode!",
          description="If this episode should exist, or is incorrect, help fix the source data here:\n"
                      "https://github.com/jp00p/AGIMUS/tree/main/data/episodes"
        ),
        ephemeral=True
      )
  except Exception as e:
    logger.info(f">>> ERROR: {e}")
