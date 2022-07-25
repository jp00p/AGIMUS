from common import *
from utils.check_channel_access import access_check
from utils.media_utils import *
from utils.timekeeper import *

command_config = config["commands"]["clip post"]

# Load JSON Data
f = open(command_config["data"])
clip_data = json.load(f)
f.close()

async def clip_autocomplete(ctx:discord.AutocompleteContext):
  clip_keys = clip_data.keys()
  return [key for key in clip_keys if ctx.value.lower() in key.lower()]

# Create drop Slash Command Group
clip = bot.create_group("clip", "Clip Commands!")

# clip_list() - Entrypoint for `/clip list`` command
# List the available clips by key and send to user as ephemeral
@clip.command(
  name="list",
  description="Retrieve the List of Clips",
)
async def clips_list(ctx:discord.ApplicationContext):
  logger.info(f"{Fore.RED}Firing `/clips list` command, requested by {ctx.author.name}!{Fore.RESET}")
  clips_list = "\n".join(clip_data)
  embed = discord.Embed(
    title="List of Clips",
    description=clips_list,
    color=discord.Color.blue()
  )
  user = get_user(ctx.author.id)
  if user['receive_notifications']:
    try:
      await ctx.author.send(embed=embed)
      await ctx.respond(f"{get_emoji('tendi_smile_happy')} Sent you a DM with the full List of Clips!", ephemeral=True)
    except:
      await ctx.respond(embed=embed, ephemeral=True)
  else:
    await ctx.respond(embed=embed, ephemeral=True)


# clip_post() - Entrypoint for `/clip post` command
# Parses a query, determines if it's allowed in the channel,
# and if allowed retrieve from metadata to do matching and
# then send the .mp4 file
@clip.command(
  name="post",
  description="Send a clip to the channel or to just yourself via the <private> option",
)
@option(
  name="query",
  description="Which clip? NOTE: Uses autocomplete, start typing and it should show relevant results!",
  required=True,
  autocomplete=clip_autocomplete
)
@option(
  name="private",
  description="Send clip to just yourself?",
  required=False
)
@commands.check(access_check)
async def clip_post(ctx:discord.ApplicationContext, query:str, private:bool):
  logger.info(f"{Fore.RED}Firing `/clip post` command, requested by {ctx.author.name}!{Fore.RESET}")
  # Private drops are not on the timer
  clip_allowed = True
  if not private:
    clip_allowed = await check_timekeeper(ctx)

  if clip_allowed:
    q = query.lower().strip()
    clip_metadata = get_media_metadata(clip_data, q)

    if clip_metadata:
      try:
        filename = get_media_file(clip_metadata)
        await ctx.respond(file=discord.File(filename), ephemeral=private)
        if not private:
          set_timekeeper(ctx)
      except BaseException as err:
        logger.info(f"{Fore.RED}ERROR LOADING CLIP: {err}{Fore.RESET}")
    else:
      await ctx.respond(f"{get_emoji('ezri_frown_sad')} Clip not found! To get a list of clips run: /clips list", ephemeral=True)
  else:
    await ctx.respond(f"{get_emoji('ohno')} Someone in the channel has already posted a clip too recently. Please wait a minute before another clip!", ephemeral=True)
