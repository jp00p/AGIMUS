import re
import requests
import urllib.parse

from .common import *
from utils.check_channel_access import *


# nexttrek() - Entrypoint for /nexttrek command
# Retrieve the next Trek episode, or next episode for a specific show
nexttrek_config = config["commands"]["nexttrek"]

@slash.slash(
  name="nexttrek",
  description="Retrieve info on the next Trek episode!",
  guild_ids=config["guild_ids"],
    options=[
      create_option(
        name="show",
        description="Which show?",
        required=True,
        option_type=3,
        choices=[
          create_choice(
            name="Lower Decks",
            value="lowerdecks"
          ),
          create_choice(
            name="Picard",
            value="picard"
          ),
          create_choice(
            name="Prodigy",
            value="prodigy"
          ),
          create_choice(
            name="Strange New Worlds",
            value="snw"
          )
        ]
    )
  ]
)
@slash_check_channel_access(nexttrek_config)
async def nexttrek(ctx:SlashContext, show:str):
  tvmaze_ids = {
    "lowerdecks": 39323,
    "picard": 42193,
    "prodigy": 49333,
    "snw": 48090,
  }
  show_id = tvmaze_ids.get(show)
  try:
    show_data = requests.get(f"https://api.tvmaze.com/shows/{show_id}").json()
    show_name = show_data["name"]
    next_episode = show_data["_links"].get("nextepisode")
    if (next_episode == None):
      await ctx.send(f"<:ezri_frown_sad:757762138176749608> Sorry, doesn't look like we have info scheduled for the next episode of {show_name}.", hidden=True)
    else:
      episode_data = requests.get(next_episode["href"]).json()
      embed = await get_show_embed(show_data, episode_data)
      await ctx.send(embed=embed)
  except BaseException as err:
    logger.error(err)
    await ctx.send("<a:emh_doctor_omg_wtf_zoom:865452207699394570> Sorry, something went wrong with the request!", hidden=True)


# nextep() - Entrypoint for /nextep command
# Retrieve the next episode of any given show query
nextep_config = config["commands"]["nextep"]

@slash.slash(
  name="nextep",
  description="Retrieve info on the next episode of a given show!",
  guild_ids=config["guild_ids"],
    options=[
      create_option(
        name="query",
        description="Which show?",
        required=True,
        option_type=3,
    )
  ]
)
@slash_check_channel_access(nextep_config)
async def nextep(ctx:SlashContext, query:str):
  encoded_query = urllib.parse.quote(query, safe='')
  try:
    show_lookup = requests.get(f"https://api.tvmaze.com/singlesearch/shows?q={encoded_query}")
    if show_lookup.status_code == 404:
      await ctx.send("<a:emh_doctor_omg_wtf_zoom:865452207699394570> Sorry, no show matches your query!", hidden=True)
      return

    show_data = show_lookup.json()
    show_name = show_data["name"]
    next_episode = show_data["_links"].get("nextepisode")
    if (next_episode == None):
      await ctx.send(f"<:ezri_frown_sad:757762138176749608> Sorry, doesn't look like we have info scheduled for the next episode of {show_name}.", hidden=True)
    else:
      episode_data = requests.get(next_episode["href"]).json()
      embed = await get_show_embed(show_data, episode_data)
      await ctx.send(embed=embed)
  except BaseException as err:
    logger.error(err)
    await ctx.send("<a:emh_doctor_omg_wtf_zoom:865452207699394570> Sorry, something went wrong with the request!", hidden=True)


async def get_show_embed(show_data, episode_data):
  show_name = show_data["name"]
  # Embed Template
  embed = discord.Embed(
    title=f"Next episode for {show_name}",
    color=discord.Color.blue()
  )
  embed.set_thumbnail(url=show_data["image"]["medium"])
  # Summary (Remove HTML tags)
  # Title
  embed.add_field(
    name="Title",
    value=episode_data['name'],
    inline=False
  )
  summary = re.sub('<[^<]+?>', '', episode_data["summary"])
  embed.add_field(
    name="Summary",
    value=summary,
    inline=False
  )
  # Number
  season_number = episode_data["season"]
  episode_number = episode_data["number"]
  episode_number = f"Season {season_number}, Episode {episode_number}"
  embed.add_field(
    name="Episode Number",
    value=episode_number,
    inline=True
  )
  # Airdate
  embed.add_field(
    name="Airdate",
    value=episode_data["airdate"],
    inline=True
  )
  return embed
