from .common import *
import re
from os.path import exists

# info() - Entrypoint for !info command
# message[required]: discord.Message
# This function is the main entrypoint of the !info command
async def info(message:discord.Message):
  user_command = message.content.lower().replace("!info ", "").split()
  found = False
  if len(user_command) == 2:
    show_key = user_command[0]
    raw_season_episode = user_command[1]
    if  exists("./data/episodes/" + show_key + ".json"):
      f = open("./data/episodes/" + show_key + ".json")
      show_data = json.load(f)
      f.close()
      season = re.sub(r'e.*', '', raw_season_episode).replace("s","")
      episode = re.sub(r'.*e', '', raw_season_episode)
      logger.info(f"{show_key} {season}x{episode}")
      show_index = -1
      for ep in show_data["episodes"]:
        show_index = show_index + 1
        if ep["season"] == season and ep["episode"] == episode:
          found = True
          break
  if found:
    display_embed = await get_show(show_data, show_index, show_key)
    embed=discord.Embed(title=display_embed["title"], \
      url=display_embed["url"], \
      description=display_embed["description"], \
      color=0xFFFFFF)
    embed.set_thumbnail(url=display_embed["still"])
    await message.channel.send(embed=embed)
  else:
    await message.channel.send("Could not find this episode.\n" \
      + "Usage: `!info [show] [s##e##]`\n" \
      + "show: " + '|'.join(config["commands"]["info"]["parameters"][0]["allowed"]) + "\n" \
      + "If this episode should exist, or is incorrect, help fix the source data here:\n" \
      + "https://github.com/jp00p/FoDBot-SQL/tree/main/data/episodes")


async def get_show(show_data, show_index, show_key):
  logger.info(f"get_show(show_data, {show_index}, {show_key})")
  tep = show_data["episodes"][show_index]
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

