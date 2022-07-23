from common import *


@bot.slash_command(
  name="speak",
  description="Make AGIMUS send an announcement (or other message!)"
)
@option(
  name="content",
  description="The content of the message (use <br> for newlines)",
  required=True
)
@option(
  name="dry_run",
  description="Only post a preview viewable by you",
  required=True,
  choices=[
    discord.OptionChoice(
      name="Yes",
      value="yes"
    ),
    discord.OptionChoice(
      name="No",
      value="no"
    )
  ]
)
@option(
  name="channel",
  description="Send to a channel besides AGIMUS' speaker?",
  required=False
)
@commands.has_role(config["roles"]["agimus_maintainers"])
# make agimus talk!
async def speak(ctx:discord.ApplicationContext, content:str, dry_run:str, channel:discord.TextChannel):
  try:
    content = content.replace("<br>", "\n")
    dry_run = bool(dry_run == "yes")
    if not channel:
      # default to announcement channel
      channel = bot.get_channel(get_channel_id(config["agimus_announcement_channel"]))
    if dry_run:
      await ctx.respond(content, ephemeral=dry_run)
    else:
      await channel.send(content)
      await ctx.respond(f"Your message has been sent to {channel.name}!", ephemeral=True)
  except Exception as e:
    logger.info(f"Something went wrong with /speak!")
  
    

@speak.error
async def speak_error(ctx, error):
  if isinstance(error, commands.MissingRole):
    await ctx.respond("You do not have the power nor the bravery to force AGIMUS to do that.", ephemeral=True)
  else:
    await ctx.respond("Sensoars indicate some kind of ...*error* has occured!", ephemeral=True)
