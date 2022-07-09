from common import *

from utils.check_channel_access import access_check
from utils.show_utils import get_show_embed


# randomep() - Entrypoint for !randomep command
# message[required]: discord.Message
# This function is the main entrypoint of the !randomep command
# and will return a random episode of the shows listed in the data/episodes directory
@bot.slash_command(
  name="randomep",
  description="Retrieve info on a random episode of Trek or Non-Trek Shows",
    options=[
      discord.Option(
        name="show",
        description="Which show?",
        required=True
    )
  ]
)
@commands.check(access_check)
async def randomep(ctx:discord.ApplicationContext, show:str):
  logger.info(f"{Fore.LIGHTGREEN_EX}Selected Show:{Fore.RESET} {Style.BRIGHT}{show}{Style.RESET_ALL}")
  trek = ["tos", "tas", "tng", "ds9", "voy", "enterprise", "lowerdecks", "disco", "picard"]
  nontrek = ["friends", "firefly", "simpsons", "sunny"]
  any = trek + nontrek
  if show in config["commands"]["randomep"]["parameters"][0]["allowed"]:
    if show == "trek":
      selected_show = random.choice(trek)
    elif show == "nontrek":
      selected_show = random.choice(nontrek)
    elif show == "any":
      selected_show = random.choice(any)
    else:
      selected_show = show
  else:
    invalid_embed = discord.Embed(
      title=f"Sorry your selection '**{show}**' is not supported.",
      description=f"You can use either 'trek', 'nontrek', 'any' or one of the options listed below.",
      color=discord.Color.dark_red()
    )
    invalid_embed.add_field(name="Trek Shows:", value="\n".join(sorted(trek)))
    invalid_embed.add_field(name="Non-Trek Shows:", value="\n".join(sorted(nontrek)))
    await ctx.respond(
      embed=invalid_embed,
      ephemeral=True
    )
    return
  f = open("./data/episodes/" + selected_show + ".json")
  show_data = json.load(f)
  f.close()
  episode = random.randrange(len(show_data["episodes"]))
  show_embed = get_show_embed(show_data, episode, selected_show)
  await ctx.respond(embed=show_embed)
  logger.info(f"{Fore.LIGHTGREEN_EX}Random episode finished!{Fore.RESET}")
