import random

import discord


def get_show_embed(show_data: dict, episode_index: int, show: str) -> discord.Embed:
  """
  Create a standardized embed for an episode.  `show_data` must match the format of one of the data/episodes/*.json
  files.
  """
  ep = show_data["episodes"][episode_index]

  # Gather info about MemoryAlpha and IMDB Results
  # If memoryalpha url exists, use that, if not use imdb.
  # If neither exist, use this picture:
  display_url = "https://i.imgur.com/quQnKnk.jpeg"
  imdb = ''
  if ep["imdb"]:
    display_url = f"https://www.imdb.com/title/{ep['imdb']}"
    imdb = f"[imdb]({display_url})"

  memoryalpha = ''
  if ep["memoryalpha"]:
    display_url = f"https://memory-alpha.fandom.com/wiki/{ep['memoryalpha']}"
    memoryalpha = f"[memoryalpha]({display_url})"

  # Initialize Embed with Title and URL Info
  embed = discord.Embed(
    title=f"{show_data['title']}\nS{ep['season']}E{ep['episode']} - {ep['title']}",
    url=display_url,
    description=ep["description"],
    color=0xFFFFFF
  )

  # Add Podcast Fields
  if ep["podcasts"]:
    for pod in ep["podcasts"]:
      embed.add_field(
        name=pod['title'],
        value=f"[{pod['episode']}]({pod['link']})",
        inline=False
      )

  # Add IMDB and Memory Alpha Fields
  if imdb:
    embed.add_field(name="IMDB", value=imdb)
  if memoryalpha:
    embed.add_field(name="Memory Alpha", value=memoryalpha)

  # Set Footer with Airdate Info
  if ep['airdate']:
    embed.set_footer(text=f"Airdate: {ep['airdate']}")

  # Add Thumbnail
  image_url = "https://i.imgur.com/quQnKnk.jpeg"
  if ep['stills']:
    image_url = random.choice(ep["stills"])
  embed.set_thumbnail(url=image_url)

  return embed
