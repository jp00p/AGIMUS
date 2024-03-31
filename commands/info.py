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

async def title_autocomplete(ctx: discord.AutocompleteContext):
  show = ctx.options['show']
  if exists(f"./data/episodes/{show}.json"):
    f = open(f"./data/episodes/{show}.json")
    show_data = json.load(f)
    f.close()
    episode_titles = [e['title'] for e in show_data["episodes"]]

    results = []
    for t in episode_titles:
      if ctx.value.lower() in t.lower():
        results.append(t)
    return results
  else:
    return ['Invalid Show!']

@bot.slash_command(
  name="episode_info",
  description="Get information about episodes of a show"
)
@option(
  name="show",
  description="Which show?",
  required=True,
  choices=show_choices
)
@option(
  name="episode_title",
  description="Episode Title (Search)",
  required=True,
  autocomplete=title_autocomplete
)
@commands.check(access_check)
async def info(ctx:discord.ApplicationContext, show:str, episode_title:str):
  """
  This function is the main entrypoint of the /info command
  """
  try:
    logger.info(f"{Fore.CYAN}Firing /info command!{Fore.RESET}")

    if exists(f"./data/episodes/{show}.json"):
      f = open(f"./data/episodes/{show}.json")
      show_data = json.load(f)
      f.close()

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
                        "https://github.com/jp00p/FoDBot-SQL/tree/main/data/episodes"
          ),
          ephemeral=True
        )
    else:
      await ctx.respond(
        embed=discord.Embed(
          title="Invalid Show!",
          description="If this episode should exist, or is incorrect, help fix the source data here:\n"
                      "https://github.com/jp00p/FoDBot-SQL/tree/main/data/episodes"
        ),
        ephemeral=True
      )
  except Exception as e:
    logger.info(f">>> ERROR: {e}")
