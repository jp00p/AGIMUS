import re
from os.path import exists

from common import *
from utils.check_channel_access import access_check

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
  description="Get information about episodes of a show!"
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

def get_show_embed(show_data, episode_index, show):
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

def get_show(show_data, episode_index, show):
  logger.info(f"get_show(show_data, {episode_index}, {show})")
  tep = show_data["episodes"][episode_index]
  logger.debug(f"{tep}")
  pods = ""
  if len(tep["podcasts"]) > 0:
    for pod in tep["podcasts"]:
      pods = pods + pod["title"] \
      + ": [" + pod["episode"] + "]" \
      +"(" + pod["link"] + ")\n"
  display_title = show_data["title"] + "\n" \
    + "s" + tep["season"] + "e" + tep["episode"] + ": " \
    + tep["title"]

  # If memoryalpha url exists, use that, if not use imdb. If neither exist, use this picture:
  display_url = "https://i.imgur.com/quQnKnk.jpeg"
  imdb = "imdb"
  if tep["imdb"]:
    display_url = "https://www.imdb.com/title/" + tep["imdb"]
    imdb = "[imdb](https://www.imdb.com/title/" + tep["imdb"] + ")"

  memoryalpha = ""
  if tep["memoryalpha"]:
    display_url = "https://memory-alpha.fandom.com/wiki/" + tep["memoryalpha"]
    memoryalpha = " | [memoryalpha](" + display_url + ")"

  display_description = \
    imdb + memoryalpha + "\n" \
    + pods \
    + "Airdate: " + tep["airdate"] + "\n" \
    + tep["description"]
  display_random_image = "https://i.imgur.com/quQnKnk.jpeg"
  if len(tep['stills']) > 0:
    display_random_image = random.choice(tep["stills"])
  ret = {
    "title": display_title,
    "url": display_url,
    "description": display_description,
    "still": display_random_image
  }
  return ret

