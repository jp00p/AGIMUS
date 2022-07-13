import re
import urllib.parse

import requests
from common import *
from utils.check_channel_access import access_check

# nexttrek() - Entrypoint for /nexttrek command
# Retrieve the next Trek episode, or next episode for a specific show
nexttrek_config = config["commands"]["nexttrek"]

@bot.slash_command(
  name="nexttrek",
  description="Retrieve info on the next Trek episode",
)
@option(
  name="show",
  description="Which show?",
  required=True,
  choices=[
    discord.OptionChoice(
      name="Lower Decks",
      value="lowerdecks"
    ),
    discord.OptionChoice(
      name="Picard",
      value="picard"
    ),
    discord.OptionChoice(
      name="Prodigy",
      value="prodigy"
    ),
    discord.OptionChoice(
      name="Strange New Worlds",
      value="snw"
    )
  ]
)
@commands.check(access_check)
async def nexttrek(ctx, show:str):
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
      await ctx.respond(f"{get_emoji('ezri_frown_sad')} Sorry, doesn't look like we have info scheduled for the next episode of {show_name}.", ephemeral=True)
    else:
      episode_data = requests.get(next_episode["href"]).json()
      embed = await get_next_episode_embed(show_data, episode_data)
      await ctx.respond(embed=embed)
  except BaseException as err:
    logger.error(err)
    await ctx.respond(f"{get_emoji('emh_doctor_omg_wtf_zoom')} Sorry, something went wrong with the request!", ephemeral=True)


# nextep() - Entrypoint for /nextep command
# Retrieve the next episode of any given show query
nextep_config = config["commands"]["nextep"]

@bot.slash_command(
  name="nextep",
  description="Retrieve info on the next episode of a given show!",
    options=[
      discord.Option(
        name="query",
        description="Which show?",
        required=True
    )
  ]
)
@commands.check(access_check)
async def nextep(ctx, query:str):
  encoded_query = urllib.parse.quote(query, safe='')
  try:
    show_lookup = requests.get(f"https://api.tvmaze.com/singlesearch/shows?q={encoded_query}")
    if show_lookup.status_code == 404:
      await ctx.respond(f"{get_emoji('ohno')} Sorry, no show matches your query!", ephemeral=True)
      return

    show_data = show_lookup.json()
    show_name = show_data["name"]
    next_episode = show_data["_links"].get("nextepisode")
    if (next_episode == None):
      await ctx.respond(f"{get_emoji('ezri_frown_sad')} Sorry, doesn't look like we have info scheduled for the next episode of {show_name}.", ephemeral=True)
    else:
      episode_data = requests.get(next_episode["href"]).json()
      embed = await get_next_episode_embed(show_data, episode_data)
      await ctx.respond(embed=embed)
  except BaseException as err:
    logger.error(err)
    logger.error(traceback.format_exc())
    await ctx.respond(f"{get_emoji('emh_doctor_omg_wtf_zoom')} Sorry, something went wrong with the request!", ephemeral=True)


async def get_next_episode_embed(show_data, episode_data):
  show_name = show_data["name"]
  # Embed Template
  embed = discord.Embed(
    title=f"Next episode for {show_name}",
    color=discord.Color.blue()
  )
  embed.set_thumbnail(url=show_data["image"]["medium"])
  # Title
  embed.add_field(
    name="Title",
    value=episode_data['name'],
    inline=False
  )
  # Summary (Remove HTML tags)
  if episode_data["summary"]:
    summary = re.sub('<[^<]+?>', '', episode_data["summary"])
    embed.add_field(
      name="Summary",
      value=f"||{summary}||",
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
  if episode_data["airdate"]:
    embed.add_field(
      name="Airdate",
      value=episode_data["airdate"],
      inline=True
    )
  if episode_data["airstamp"]:
    now = datetime.now(timezone.utc)
    airstamp = dateutil.parser.isoparse(episode_data["airstamp"])
    time_from_now = humanize.naturaldelta(airstamp - now)
    embed.set_footer(
      text=f"{time_from_now} from now."
    )
  return embed
