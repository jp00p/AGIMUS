from common import *

from .info import get_show


# randomep() - Entrypoint for !randomep command
# message[required]: discord.Message
# This function is the main entrypoint of the !randomep command
# and will return a random episode of the shows listed in the data/episodes directory
async def randomep(message:discord.Message):
  randomep_spl = message.content.lower().replace("!randomep ", "").split()
  logger.info(f"{Fore.LIGHTGREEN_EX}Selected Show:{Fore.RESET} {Style.BRIGHT}{randomep_spl[0]}{Style.RESET_ALL}")
  trek = ["tos", "tas", "tng", "ds9", "voy", "enterprise", "lowerdecks", "disco", "picard"]
  nontrek = ["friends", "firefly", "simpsons", "sunny"]
  any = trek + nontrek
  if randomep_spl[0] in config["commands"]["randomep"]["parameters"][0]["allowed"]:
    if randomep_spl[0] == "trek":
      selected_show = random.choice(trek)
    elif randomep_spl[0] == "nontrek":
      selected_show = random.choice(nontrek)
    elif randomep_spl[0] == "any":
      selected_show = random.choice(any)
    else:
      selected_show = randomep_spl[0]
  else:
    selected_show = random.choice(trek)
  f = open("./data/episodes/" + selected_show + ".json")
  show_data = json.load(f)
  f.close()
  episode = random.randrange(len(show_data["episodes"]))
  display_embed = await get_show(show_data, episode, selected_show)
  embed=discord.Embed(title=display_embed["title"], url=display_embed["url"], description=display_embed["description"], color=0xFFFFFF)
  embed.set_thumbnail(url=display_embed["still"])
  await message.channel.send(embed=embed)
  logger.info(f"{Fore.LIGHTGREEN_EX}Random episode finished!{Fore.RESET}")
