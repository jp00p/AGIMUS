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



class SpeakEmbed(discord.ui.Modal):
  def __init__(self, dry_run, channel):
    super().__init__(title="Embed Details")
    self.dry_run = dry_run
    self.channel = channel
    self.add_item(discord.ui.InputText(label="Title", placeholder="Embed Title"))
    self.add_item(
      discord.ui.InputText(
        label="Description",
        value="",
        style=discord.InputTextStyle.long
      )
    )

  async def callback(self, interaction:discord.Interaction):
    title = self.children[0].value
    description = self.children[1].value
    embed = discord.Embed(
      title=title,
      description=description,
      color=discord.Color(0x7C2926)
    )
    if self.channel:
      self.channel.send(embed=embed)
      await interaction.response.send_message(f"Your message has been sent to {self.channel.name}!", ephemeral=True)
    else:
      await interaction.response.send_message(embed=embed, ephemeral=self.dry_run)


@bot.slash_command(
  name="speak_embed",
  description="Make AGIMUS send an announcement (or other message!) as an embed"
)
@option(
  name="dry_run",
  description="Only post a preview viewable by you (note this does not work `channel` option!)",
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
async def speak_embed(ctx:discord.ApplicationContext, dry_run:str, channel:discord.TextChannel):
  try:
    dry_run = bool(dry_run == "yes")
    modal = SpeakEmbed(dry_run, channel)
    await ctx.interaction.response.send_modal(modal)
  except Exception as e:
    logger.info(f"Something went wrong with /speak!")
    logger.info(traceback.format_exc())

@speak_embed.error
async def speak_error(ctx, error):
  if isinstance(error, commands.MissingRole):
    await ctx.respond("You do not have the power nor the bravery to force AGIMUS to do that.", ephemeral=True)
  else:
    await ctx.respond("Sensoars indicate some kind of ...*error* has occured!", ephemeral=True)