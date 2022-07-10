from inspect import trace
from common import *
from utils.check_channel_access import access_check

# help() - Entrypoint for /help command
# This function is the main entrypoint of the /help command
# and will display each help message in the channel that it was
# initiated, for the channel it was initiated.
@bot.slash_command(
  name="help",
  description="Display a help message for the current channel-specific commands"
)
@commands.check(access_check)
async def help(ctx:discord.ApplicationContext):
  try:
    f = open(config["commands"]["help"]["data"])
    help_data = json.load(f)
    f.close()

    found_command = False
    for help_page in help_data:
      if ctx.channel.id in get_channel_ids_list(help_page["channels"]) and help_page["enabled"]:
        text_file = open(help_page["file"], "r")
        help_text = text_file.read()
        text_file.close()

        await ctx.respond(embed=discord.Embed(
          description=help_text,
          color=discord.Color.dark_gold()
        ))
        found_command = True

    if not found_command:
      await ctx.respond(embed=discord.Embed(
        title=f"No Channel-Specific Commands Found for {ctx.channel.name}"
      ))
  except BaseException as e:
    logger.info(">>> Encountered error in /help")
    logger.info(traceback.format_exc())
