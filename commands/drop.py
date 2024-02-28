from common import *
from utils.check_channel_access import access_check
from utils.media_utils import *
from utils.timekeeper import *

command_config = config["commands"]["drop post"]

# Load JSON Data
f = open(command_config["data"])
drop_data = json.load(f)
f.close()


async def drop_autocomplete(ctx: discord.AutocompleteContext):
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
async def drop_list(ctx: discord.ApplicationContext):
  """
  Entrypoint for `/drops list`` command
  List the available drops by key and send to user as ephemeral
  """
  logger.info(
    f"{Fore.RED}Firing `/drop list` command, requested by {ctx.author.name}!{Fore.RESET}")

  drop_names = drop_data.keys()
  drop_pages = ['']

  for drop_name in drop_names:
    # 4000 char to give a reasonable buffer for the 4096 char limit for embed description field
    # N.B., the longest drop name at time of authoring is "He Just Kept Talking In One Long Incredibly Unbroken Sentence" at 61 chars
    # there may be a more precise and long term reliable way to do this using `embed.len()` but modifying the `embed` after it's constructed seems like a PITA --thousand
    if len(drop_pages[-1]) > 4000:
      drop_pages.append('')
    sep = '\n' if len(drop_pages[-1]) > 0 else ''
    drop_pages[-1] += f"{sep}{drop_name}"

  # Aggy's avatar for the footer
  avatar_asset = bot.user.avatar
  avatar_url = avatar_asset.with_size(128).url

  for page_idx in range(len(drop_pages)):
    embed = discord.Embed(
      title=f"List of Drops",
      description=drop_pages[page_idx],
      color=discord.Color.blue(),
    )
    embed.set_footer(
      text=f"Page {page_idx+1} of {len(drop_pages)}", icon_url=avatar_url)
    user = get_user(ctx.author.id)
    if user['receive_notifications']:
      try:
        await ctx.author.send(embed=embed)
        # Don't do this notice more than once, that would be silly
        if page_idx == 0:
          await ctx.respond(f"{get_emoji('tendi_smile_happy')} Sent you a DM with the full List of Drops!", ephemeral=True)
        else:
          pass  # noop
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
async def drop_post(ctx: discord.ApplicationContext, public: str, query: str):
  """
  Entrypoint for `/drops post` command
  Parses a query, determines if it's allowed in the channel,
  and if allowed retrieve from metadata to do matching and
  then send the .mp4 file
  """
  logger.info(
    f"{Fore.RED}Firing `/drop post` command, requested by {ctx.author.name}!{Fore.RESET}")
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
        await ctx.respond(embed=discord.Embed(
            title="Error Retrieving Clip!",
            description="Whoops, something went wrong...",
            color=discord.Color.red()
          ), ephemeral=True
        )
    else:
      await ctx.respond(embed=discord.Embed(
          title="Drop Not Found!",
          description="To get a list of drops run: `/drops list`",
          color=discord.Color.red()
        ), ephemeral=True
      )
  else:
    await ctx.respond(embed=discord.Embed(
        title="Denied!",
        description="Someone in the channel has already dropped too recently! Please wait a minute before another drop!",
        color=discord.Color.red()
      ), ephemeral=True
    )
