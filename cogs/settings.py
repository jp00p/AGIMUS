from common import *

# ____  _____________
# \   \/  /\______   \
#  \     /  |     ___/
#  /     \  |    |
# /___/\  \ |____|
#       \_/
class XPDropdown(discord.ui.Select):
  def __init__(self, cog):
    self.cog = cog
    options = [
      discord.SelectOption(label="Enable XP", description="Opt-in to the XP and Badge System"),
      discord.SelectOption(label="Disable XP", description="Opt-out of the XP and Badge System"),
    ]

    super().__init__(
      placeholder="Choose your preference",
      min_values=1,
      max_values=1,
      options=options,
      row=1
    )

  async def callback(self, interaction:discord.Interaction):
    selection = self.values[0]

    if selection == "Enable XP":
      db_toggle_xp(interaction.user.id, True)
      await interaction.response.send_message(
        embed=discord.Embed(
          title="You have successfully chosen to participate in the XP and Badge System.",
          color=discord.Color.green()
        ).set_footer(text="You can always come back to this interface and re-enable in the future!"),
        ephemeral=True
      )
    elif selection == "Disable XP":
      db_toggle_xp(interaction.user.id, False)
      await interaction.response.send_message(
        embed=discord.Embed(
          title="You have successfully opted-out of the XP and Badge System.",
          color=discord.Color.blurple()
        ).set_footer(text="You can always come back to this interface and re-enable in the future!"),
        ephemeral=True
      )

class XPView(discord.ui.View):
  def __init__(self, cog):
    self.cog = cog
    super().__init__()

    self.add_item(XPDropdown(self.cog))


#  _______          __  .__  _____.__               __  .__
#  \      \   _____/  |_|__|/ ____\__| ____ _____ _/  |_|__| ____   ____   ______
#  /   |   \ /  _ \   __\  \   __\|  |/ ___\\__  \\   __\  |/  _ \ /    \ /  ___/
# /    |    (  <_> )  | |  ||  |  |  \  \___ / __ \|  | |  (  <_> )   |  \\___ \
# \____|__  /\____/|__| |__||__|  |__|\___  >____  /__| |__|\____/|___|  /____  >
#         \/                              \/     \/                    \/     \/
class NotificationsDropdown(discord.ui.Select):
  def __init__(self, cog):
    self.cog = cog
    options = [
      discord.SelectOption(label="Enable Notifications", description="Allow AGIMUS to send you DMs"),
      discord.SelectOption(label="Disable Notifications", description="Prevent AGIMUS from sending you DMs"),
    ]

    super().__init__(
      placeholder="Choose your preference",
      min_values=1,
      max_values=1,
      options=options,
      row=1
    )

  async def callback(self, interaction: discord.Interaction):
    selection = self.values[0]

    if selection == "Enable Notifications":
      db_toggle_notifications(interaction.user.id, True)
      await interaction.response.send_message(
        embed=discord.Embed(
          title="You have successfully allowed AGIMUS to send you DMs.",
          color=discord.Color.green()
        ).set_footer(text="You can always come back to this interface and re-enable in the future!"),
        ephemeral=True
      )
    elif selection == "Disable Notifications":
      db_toggle_notifications(interaction.user.id, False)
      await interaction.response.send_message(
        embed=discord.Embed(
          title="You have successfully disabled AGIMUS from sending you DMs",
          color=discord.Color.blurple()
        ).set_footer(text="You can always come back to this interface and re-enable in the future!"),
        ephemeral=True
      )

class NotificationsView(discord.ui.View):
  def __init__(self, cog):
    self.cog = cog
    super().__init__()

    self.add_item(NotificationsDropdown(self.cog))


#  __      __                .___     .__                   .___
# /  \    /  \___________  __| _/____ |  |   ____  __ __  __| _/
# \   \/\/   /  _ \_  __ \/ __ |/ ___\|  |  /  _ \|  |  \/ __ |
#  \        (  <_> )  | \/ /_/ \  \___|  |_(  <_> )  |  / /_/ |
#   \__/\  / \____/|__|  \____ |\___  >____/\____/|____/\____ |
#        \/                   \/    \/                       \/
class WordcloudDropdown(discord.ui.Select):
  def __init__(self, cog):
    self.cog = cog
    options = [
      discord.SelectOption(label="Enable Wordcloud", description="Allow logging."),
      discord.SelectOption(label="Disable Wordcloud", description="Disable logging. NOTE: This also clears your current logs!"),
    ]

    super().__init__(
      placeholder="Choose your preference",
      min_values=1,
      max_values=1,
      options=options,
      row=1
    )

  async def callback(self, interaction: discord.Interaction):
    selection = self.values[0]

    if selection == "Enable Wordcloud":
      db_toggle_wordcloud(interaction.user.id, True)
      await interaction.response.send_message(
        embed=discord.Embed(
          title="You have successfully allowed AGIMUS to log your common words for the purpose of generating Wordclouds.",
          color=discord.Color.green()
        ).set_footer(text="You can always come back to this interface and re-enable in the future!"),
        ephemeral=True
      )
    elif selection == "Disable Wordcloud":
      deleted_message_count = db_toggle_notifications(interaction.user.id, False)
      await interaction.response.send_message(
        embed=discord.Embed(
          title=f"You have successfully disabled AGIMUS from logging your common words and cleared any current data ({deleted_message_count} messages deleted).",
          color=discord.Color.blurple()
        ).set_footer(text="You can always come back to this interface and re-enable in the future!"),
        ephemeral=True
      )

class WordcloudView(discord.ui.View):
  def __init__(self, cog):
    self.cog = cog
    super().__init__()

    self.add_item(WordcloudDropdown(self.cog))


# _________
# \_   ___ \  ____   ____
# /    \  \/ /  _ \ / ___\
# \     \___(  <_> ) /_/  >
#  \______  /\____/\___  /
#         \/      /_____/
class Settings(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @commands.slash_command(
    name="settings",
    description="Set up your AGIMUS settings!"
  )
  async def settings(self, ctx):
    home_embed, home_thumbnail = await self._get_home_embed_and_thumbnail()

    current_xp_setting = db_get_current_xp_enabled_value(ctx.user.id)
    xp_embed, xp_thumbnail = await self._get_xp_embed_and_thumbnail(current_xp_setting)

    notifications_embed, notifications_thumbnail = await self._get_notifications_embed_and_thumbnail()
    wordcloud_embed, wordcloud_thumbnail = await self._get_wordcloud_embed_and_thumbnail()

    page_groups = [
      pages.PageGroup(
        pages=[
          pages.Page(
            embeds=[home_embed],
            files=[home_thumbnail]
          )
        ],
        label="Home",
        description="Settings Homepage and Help",
        custom_buttons=[],
      ),
      pages.PageGroup(
        pages=[
          pages.Page(
            embeds=[xp_embed],
            files=[xp_thumbnail]
          )
        ],
        label="XP",
        description="Opt-in or Opt-out of the XP System",
        custom_buttons=[],
        use_default_buttons=False,
        custom_view=XPView(self)
      ),
      pages.PageGroup(
        pages=[
          pages.Page(
            embeds=[notifications_embed],
            files=[notifications_thumbnail]
          )
        ],
        label="Notifications",
        description="Enable or Disable DMs from AGIMUS",
        custom_buttons=[],
        use_default_buttons=False,
        custom_view=NotificationsView(self)
      ),
      pages.PageGroup(
        pages=[
          pages.Page(
            embeds=[wordcloud_embed],
            files=[wordcloud_thumbnail]
          )
        ],
        label="Wordcloud",
        description="Enable or Disable Wordcloud Logging",
        custom_buttons=[],
        use_default_buttons=False,
        custom_view=WordcloudView(self)
      ),
    ]
    paginator = pages.Paginator(
      pages=page_groups,
      show_menu=True,
      menu_placeholder="Navigate To Setting",
      show_disabled=False,
      show_indicator=False,
      use_default_buttons=False,
      custom_buttons=[],
    )
    await paginator.respond(ctx.interaction, ephemeral=True)

  async def _get_home_embed_and_thumbnail(self):
    thumbnail = discord.File(fp="./images/templates/settings/settings.png", filename="settings.png")
    embed = discord.Embed(
      title="Settings",
      description="AGIMUS is The USS Hood's resident Self-Aware Megalomaniacal Computer and our Discord Bot! It has a *ton* of useful functionality and has some user preferences you can configure for features you may or may not be interested in.\n\nFor more details on what AGIMUS can do, try using `/help` in any channel. Channel-specific functionality will also be displayed if used within The Promenade channels.",
      color=discord.Color(0xFF0000)
    )
    embed.set_footer(text="Please use the dropdown below to select a category and begin.")
    embed.set_image(url="https://i.imgur.com/TfDEuSS.jpg")
    embed.set_thumbnail(url=f"attachment://settings.png")

    return embed, thumbnail

  async def _get_xp_embed_and_thumbnail(self, current_xp_value):
    badge_channel = await self.bot.fetch_channel(get_channel_id("badgeys-badges"))

    thumbnail = discord.File(fp="./images/templates/settings/xp_system.png", filename="xp_system.png")
    embed = discord.Embed(
      title="XP System Preferences",
      description=f"The XP System on the USS Hood awards users XP points for participating in the server in various ways. Some of these include posting messages, reacting to messages, and receiving reactions to your own messages.\n\nOnce you've received a set amount of XP, you will Level Up and receive a new Badge with a notification in {badge_channel.mention}. If you don't wish to participate, you can configure that here. You can always re-enable if desired in the future!",
      color=discord.Color(0xFF0000)
    )
    embed.set_footer(text="Please select your choice from the preference dropdown below.")
    embed.set_image(url="https://i.imgur.com/upuEFlq.png")
    embed.set_thumbnail(url=f"attachment://xp_system.png")

    return embed, thumbnail

  async def _get_notifications_embed_and_thumbnail(self):
    thumbnail = discord.File(fp="./images/templates/settings/notifications.png", filename="notifications.png")
    embed = discord.Embed(
      title="AGIMUS Notifications",
      description="AGIMUS may occasionally want to send you a Direct Message with useful information.\n\nSome examples include sending Drops/Clips lists when requested and notably, DMs are used in the Badge Trading System to give alerts when a trade has been initiated or one of your existing trades has been canceled.",
      color=discord.Color(0xFF0000)
    )
    embed.set_footer(text="Please select your choice from the preference dropdown below.")
    embed.set_image(url="https://i.imgur.com/XMnho37.png")
    embed.set_thumbnail(url=f"attachment://notifications.png")

    return embed, thumbnail

  async def _get_wordcloud_embed_and_thumbnail(self):
    wordcloud_blocked_channel_ids = get_channel_ids_list([
      "neelixs-morale-office",
      "plasma-vent",
      "counselor-trois-office",
      "heuristic-associative-pathways",
      "megalomaniacal-computer-storage",
      "bot-setup",
      "dabo-table",
      "poker-night",
      "morns-nonstop-quiz",
      "badgeys-badges"
    ])
    wordcloud_blocked_channels = [
      await self.bot.fetch_channel(channel_id) for channel_id in wordcloud_blocked_channel_ids
    ]
    wordcloud_blocked_channels_string = "\n\n"
    for channel in wordcloud_blocked_channels:
      wordcloud_blocked_channels_string += f"{channel.mention}\n"

    thumbnail = discord.File(fp="./images/templates/settings/wordcloud.png", filename="wordcloud.png")

    embed = discord.Embed(
      title="Wordcloud Logging",
      description=f"AGIMUS has an opt-in Wordcloud feature which you can enable to track the most common words that you use to create images which weigh each word based on frequency.\n\nIf wish to opt out in the future, your existing message data will be deleted.\n\nNote that the following channels are not included in logging for the Wordcloud: {wordcloud_blocked_channels_string}\n**Example Wordcloud:**",
      color=discord.Color(0xFF0000)
    )
    embed.set_footer(text="Please select your choice from the preference dropdown below.")
    embed.set_image(url="https://i.imgur.com/xNeoDSD.png")
    embed.set_thumbnail(url=f"attachment://wordcloud.png")

    return embed, thumbnail


def db_get_current_xp_enabled_value(user_id):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT xp_enabled FROM users WHERE discord_id = %s"
  vals = (user_id,)
  query.execute(sql, vals)
  row = query.fetchone()
  db.commit()
  query.close()
  db.close()

  return row['xp_enabled']

def db_toggle_xp(user_id, value:bool):
  db = getDB()
  query = db.cursor()
  sql = "UPDATE users SET xp_enabled = %s WHERE discord_id = %s"
  vals = (value, user_id)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()

def db_toggle_notifications(user_id, toggle):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "UPDATE users SET receive_notifications = %s WHERE discord_id = %s"
  vals = (toggle, user_id)
  query.execute(sql, vals)
  query.close()
  db.commit()
  db.close()

def db_toggle_wordcloud(user_id, toggle):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "UPDATE users SET log_messages = %s WHERE discord_id = %s"
  vals = (toggle, user_id)
  query.execute(sql, vals)

  deleted_row_count = None
  if not toggle:
    sql = "DELETE FROM message_history WHERE user_discord_id = %s"
    vals = (user_id,)
    query.execute(sql, vals)
    deleted_row_count = query.rowcount

  db.commit()
  query.close()
  db.close()

  return deleted_row_count