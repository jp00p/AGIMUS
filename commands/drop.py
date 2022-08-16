from common import *
from utils.check_channel_access import access_check
from utils.media_utils import *
from utils.timekeeper import *

command_config = config["commands"]["drop post"]

# Load JSON Data
f = open(command_config["data"])
drop_data = json.load(f)
f.close()

async def drop_autocomplete(ctx:discord.AutocompleteContext):
  results = []
  for drop_key in drop_data.keys():
    drop_info = drop_data[drop_key]
    drop_description = drop_info["description"]
    if ctx.value.lower() in drop_key.lower() or ctx.value.lower() in drop_description:
      results.append(drop_key)

  return results

# Create drop Slash Command Group
drop = bot.create_group("drop", "Drop Commands!")

@drop.command(
  name="list",
  description="Retrieve the List of Drops"
)
async def drop_list(ctx:discord.ApplicationContext):
  """
  Entrypoint for `/drops list`` command
  List the available drops by key and send to user as ephemeral
  """
  logger.info(f"{Fore.RED}Firing `/drop list` command, requested by {ctx.author.name}!{Fore.RESET}")
  drops_list = "\n".join(drop_data)
  embed = discord.Embed(
    title="List of Drops",
    description=drops_list,
    color=discord.Color.blue()
  )
  user = get_user(ctx.author.id)
  if user['receive_notifications']:
    try:
      await ctx.author.send(embed=embed)
      await ctx.respond(f"{get_emoji('tendi_smile_happy')} Sent you a DM with the full List of Drops!", ephemeral=True)
    except BaseException as e:
      await ctx.respond(embed=embed, ephemeral=True)
  else:
    await ctx.respond(embed=embed, ephemeral=True)

@drop.command(
  name="post",
  description="Send a drop to the channel or to just yourself via the <private> option",
)
@option(
  name="public",
  description="Show to public?",
  required=True,
  choices=[
    discord.OptionChoice(
      name="No",
      value="no"
    ),
    discord.OptionChoice(
      name="Yes",
      value="yes"
    )
  ]
)
@option(
  name="query",
  description="Which drop? NOTE: Uses autocomplete, start typing and it should show relevant results!",
  required=True,
  autocomplete=drop_autocomplete
)
@commands.check(access_check)
async def drop_post(ctx:discord.ApplicationContext, public:str, query:str):
  """
  Entrypoint for `/drops post` command
  Parses a query, determines if it's allowed in the channel,
  and if allowed retrieve from metadata to do matching and
  then send the .mp4 file
  """
  logger.info(f"{Fore.RED}Firing `/drop post` command, requested by {ctx.author.name}!{Fore.RESET}")
  # Private drops are not on the timer
  public = bool(public == "yes")
  allowed = True
  if public:
    allowed = await check_timekeeper(ctx)

  if (allowed):
    q = query.lower().strip()
    drop_metadata = get_media_metadata(drop_data, q)

    if drop_metadata:
      try:
        filename = get_media_file(drop_metadata)
        await ctx.respond(file=discord.File(filename), ephemeral=not public)
        if public:
          set_timekeeper(ctx)
      except Exception as err:
        logger.info(f"{Fore.RED}ERROR LOADING DROP: {err}{Fore.RESET}")
    else:
      await ctx.respond(f"{get_emoji('ezri_frown_sad')} Drop not found! To get a list of drops run: /drops list", ephemeral=True)
  else:
    await ctx.respond(f"{get_emoji('ohno')} Someone in the channel has already dropped too recently. Please wait a minute before another drop!", ephemeral=True)
