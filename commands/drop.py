from .common import *
from utils.check_channel_access import access_check
from utils.media_utils import *
from utils.timekeeper import *

command_config = config["commands"]["drop"]
emojis = config["emojis"]

# Load JSON Data
f = open(command_config["data"])
drop_data = json.load(f)
f.close()

# slash_drops() - Entrypoint for /drops command
# List the available drops by key and send to user as ephemeral
@bot.command(
  name="drops",
  description="Retrieve the List of Drops."
)
async def drops(ctx):
  drops_list = "\n".join(drop_data)
  embed = discord.Embed(
    title="List of Drops",
    description=drops_list,
    color=discord.Color.blue()
  )
  try:
    await ctx.author.send(embed=embed)
    await ctx.respond(f"{emojis.get('tendi_smile_happy')} Sent you a DM with the full List of Drops!", ephemeral=True)
  except BaseException as e:
    await ctx.respond(embed=embed, ephemeral=True)

# drop() - Entrypoint for /drops command
# Parses a query, determines if it's allowed in the channel,
# and if allowed retrieve from metadata to do matching and
# then send the .mp4 file
@bot.slash_command(
  name="drop",
  description="Send a drop to the channel!",
)
@option(
  name="query",
  description="Which drop?",
  required=True,
)
@option(
  name="private",
  description="Send drop to just yourself?",
  required=False,
)
@commands.check(access_check)
async def drop(ctx:discord.ApplicationContext, query:str, private:bool):
  logger.info(f"{Fore.RED}Firing drop command!{Fore.RESET}")
  # Private drops are not on the timer
  drop_allowed = True
  if not private:
    drop_allowed = await check_timekeeper(ctx)

  if (drop_allowed):  
    q = query.lower().strip()
    drop_metadata = get_media_metadata(drop_data, q)

    if drop_metadata:
      try:
        filename = get_media_file(drop_metadata)
        await ctx.respond(file=discord.File(filename), ephemeral=private)
        if not private:
          set_timekeeper(ctx)
      except BaseException as err:
        logger.info(f"{Fore.RED}ERROR LOADING DROP: {err}{Fore.RESET}")
        userid = command_config.get("error_contact_id")
        if userid:
          await ctx.respond(f"{emojis.get('emh_doctor_omg_wtf_zoom')} Something has gone horribly awry, we may have a coolant leak. Contact Lieutenant Engineer <@{userid}>", ephemeral=True)  
    else:
      await ctx.respond(f"{emojis.get('ezri_frown_sad')} Drop not found! To get a list of drops run: /drops", ephemeral=True)
  else:
    await ctx.respond(f"{emojis.get('ohno')} Someone in the channel has already dropped too recently. Please wait a minute before another drop!", ephemeral=True)
