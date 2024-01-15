from common import *
from cogs.trade import db_is_user_in_dtd_list

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
        ).set_footer(text="You can always come back to this interface to reconfigure in the future!"),
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
        ).set_footer(text="You can always come back to this interface and reconfigure in the future!"),
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
        ).set_footer(text="You can always come back to this interface and reconfigure in the future!"),
        ephemeral=True
      )
    elif selection == "Disable Wordcloud":
      deleted_message_count = db_toggle_wordcloud(interaction.user.id, False)
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


# .____                    .______.           __
# |    |    ____  __ __  __| _/\_ |__   _____/  |_
# |    |   /  _ \|  |  \/ __ |  | __ \ /  _ \   __\
# |    |__(  <_> )  |  / /_/ |  | \_\ (  <_> )  |
# |_______ \____/|____/\____ |  |___  /\____/|__|
#         \/                \/      \/
class LoudbotDropdown(discord.ui.Select):
  def __init__(self, cog):
    self.cog = cog
    options = [
      discord.SelectOption(label="Enable Loudbot", description="Allow Loudbot auto-responses and log messages."),
      discord.SelectOption(label="Disable Loudbot", description="Disable Loudbot and clear existing logged messages.")
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

    if selection == "Enable Loudbot":
      db_toggle_loudbot(interaction.user.id, True)
      await interaction.response.send_message(
        embed=discord.Embed(
          title=f"You have successfully allowed AGIMUS to auto-respond to your all-caps messages and log them for parroting in the future.",
          color=discord.Color.green()
        ).set_footer(text="You can always come back to this interface and reconfigure in the future!"),
        ephemeral=True
      )
    elif selection == "Disable Loudbot":
      deleted_message_count = db_toggle_loudbot(interaction.user.id, False)
      await interaction.response.send_message(
        embed=discord.Embed(
          title=f"You have successfully disabled AGIMUS auto-responding to your all-caps messages and logging messages for the purpose of parroting them in the future. Cleared {deleted_message_count} messages.",
          color=discord.Color.blurple()
        ).set_footer(text="You can always come back to this interface and re-enable in the future!"),
        ephemeral=True
      )

class LoudbotView(discord.ui.View):
  def __init__(self, cog):
    self.cog = cog
    super().__init__()

    self.add_item(LoudbotDropdown(self.cog))


# ________                        ___________      ________        ___.
# \______ \   ______  _  ______   \__    ___/___   \______ \ _____ \_ |__   ____
#  |    |  \ /  _ \ \/ \/ /    \    |    | /  _ \   |    |  \\__  \ | __ \ /  _ \
#  |    `   (  <_> )     /   |  \   |    |(  <_> )  |    `   \/ __ \| \_\ (  <_> )
# /_______  /\____/ \/\_/|___|  /   |____| \____/  /_______  (____  /___  /\____/
#         \/                  \/                           \/     \/    \/
class DTDDropdown(discord.ui.Select):
  def __init__(self, cog):
    self.cog = cog
    options = [
      discord.SelectOption(label="Enable DTD", description="Opt-in to the Down To Dabo List"),
      discord.SelectOption(label="Disable DTD", description="Opt-out of the Down To Dabo List"),
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

    is_user_in_dtd_already = db_is_user_in_dtd_list(interaction.user.id)

    if selection == "Enable DTD":
      if is_user_in_dtd_already:
        await interaction.response.send_message(
          embed=discord.Embed(
            title="You're already in the DTD List! No action taken.",
            color=discord.Color.red()
          ),
          ephemeral=True
        )
      else:
        db_add_user_to_dtd(interaction.user.id)
        await interaction.response.send_message(
          embed=discord.Embed(
            title="You have successfully chosen to participate in the Down To Dabo List.",
            color=discord.Color.green()
          ).set_footer(text="You can always come back to this interface to reconfigure in the future!"),
          ephemeral=True
        )
    elif selection == "Disable DTD":
      if not is_user_in_dtd_already:
        await interaction.response.send_message(
          embed=discord.Embed(
            title="You weren't in the DTD list! No action taken.",
            color=discord.Color.red()
          ),
          ephemeral=True
        )
      else:
        db_remove_user_from_dtd(interaction.user.id)
        await interaction.response.send_message(
          embed=discord.Embed(
            title="You have successfully opted-out of the Down To Dabo List.",
            color=discord.Color.blurple()
          ).set_footer(text="You can always come back to this interface and re-enable in the future!"),
          ephemeral=True
        )

class DTDView(discord.ui.View):
  def __init__(self, cog):
    self.cog = cog
    super().__init__()

    self.add_item(DTDDropdown(self.cog))


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
    description="Configure your AGIMUS settings!"
  )
  async def settings(self, ctx):
    await ctx.defer(ephemeral=True)
    home_embed, home_thumbnail = await self._get_home_embed_and_thumbnail()

    current_xp_setting = db_get_current_xp_enabled_value(ctx.user.id)
    xp_embed, xp_thumbnail = await self._get_xp_embed_and_thumbnail(current_xp_setting)

    notifications_embed, notifications_thumbnail = await self._get_notifications_embed_and_thumbnail()
    wordcloud_embed, wordcloud_thumbnail = await self._get_wordcloud_embed_and_thumbnail()
    loudbot_embed, loudbot_thumbnail = await self._get_loudbot_embed_and_thumbnail()
    dtd_embed, dtd_thumbnail = await self._get_dtd_embed_and_thumbnail()

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
      pages.PageGroup(
        pages=[
          pages.Page(
            embeds=[loudbot_embed],
            files=[loudbot_thumbnail]
          )
        ],
        label="Loudbot",
        description="Enable or Disable Loudbot Auto-Responses and Logging",
        custom_buttons=[],
        use_default_buttons=False,
        custom_view=LoudbotView(self)
      ),
      pages.PageGroup(
        pages=[
          pages.Page(
            embeds=[dtd_embed],
            files=[dtd_thumbnail]
          )
        ],
        label="Down To Dabo",
        description="Opt-in or Opt-out of the Down To Dabo List",
        custom_buttons=[],
        use_default_buttons=False,
        custom_view=DTDView(self)
      )
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
      description="The XP System on the USS Hood awards users XP for participating in the server in "
                  "various ways. Some of these include posting messages, reacting to messages, and "
                  "receiving reactions to your own messages.\n\nOnce you've received a set amount of "
                  "XP, you will Level Up and receive a new Badge with a notification in "
                  f"{badge_channel.mention}. You can start typing `/badges` to see the various "
                  "badge-specific commands available for taking a look at your collection!\n\nIf you "
                  "don't wish to participate, you can configure that here. You can always re-enable "
                  "if desired in the future!",
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
      description="AGIMUS may occasionally want to send you a Direct Message with useful information."
                  "\n\nSome examples include sending Drops/Clips lists when requested and notably, DMs "
                  "are used in the Badge Trading System to give alerts when a trade has been initiated "
                  "or one of your existing trades has been canceled.",
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
      "counselor-trois-waiting-room",
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
      description="AGIMUS has an opt-in Wordcloud feature which you can enable to track the most common "
                  "words that you use. When the command is executed with `/wordcloud` a new image is "
                  "generated which weighs each word based on frequency.\n\nIf wish to opt out in the "
                  "future, your existing message data will be deleted.\n\nNote that the following "
                  "channels are not included in logging for the Wordcloud: "
                  f"{wordcloud_blocked_channels_string}\n**Example Wordcloud:**",
      color=discord.Color(0xFF0000)
    )
    embed.set_footer(text="Please select your choice from the preference dropdown below.")
    embed.set_image(url="https://i.imgur.com/xNeoDSD.png")
    embed.set_thumbnail(url=f"attachment://wordcloud.png")

    return embed, thumbnail

  async def _get_loudbot_embed_and_thumbnail(self):
    loudbot_enabled_channel_ids = get_channel_ids_list([
      "after-dinner-conversation",
      "badgeys-badges",
      "bahrats-bazaar",
      "dabo-table",
      "dr-crushers-hotbox",
      "megalomaniacal-computer-storage",
      "morns-nonstop-quiz",
      "poker-night",
      "seskas-catfishing-channel",
      "ten-forward",
      "temba-his-arms-wide"
    ])
    loudbot_enabled_channels = [
      await self.bot.fetch_channel(channel_id) for channel_id in loudbot_enabled_channel_ids
    ]
    loudbot_enabled_channels_string = "\n\n"
    for channel in loudbot_enabled_channels:
      loudbot_enabled_channels_string += f"{channel.mention}\n"

    thumbnail = discord.File(fp="./images/templates/settings/loudbot.png", filename="loudbot.png")

    embed = discord.Embed(
      title="Loudbot Auto-Responses and Logging",
      description="AGIMUS has an opt-in Loudbot feature which you can enable to allow to have it auto-respond "
                  "to messages you post that are in all-caps. When your message is registered it also logs the "
                  "message to be used as a response to other users who have the feature enabled.\n\nIf wish to "
                  "opt out in the future, your existing message data will be deleted.\n\nNote that the following "
                  f"channels are where Loudbot is allowed to auto-respond: {loudbot_enabled_channels_string}",
      color=discord.Color(0xFF0000)
    )
    embed.set_footer(text="Please select your choice from the preference dropdown below.")
    embed.set_image(url="https://i.imgur.com/wq34YDD.png")
    embed.set_thumbnail(url=f"attachment://loudbot.png")

    return embed, thumbnail

  async def _get_dtd_embed_and_thumbnail(self):
    thumbnail = discord.File(fp="./images/templates/settings/dtd.png", filename="dtd.png")
    embed = discord.Embed(
      title="Down To Dabo",
      description="Users doing trading in <#1006265911428272239> can use the `/trade dabo` command which "
                  "randomly selects a number of badges from both user's unlocked inventories to swap.\n\n"
                  "There's an additional command `/trade dtd` which will return a weighted randomized user "
                  "from those who have opted-in to the Down To Dabo List. Select below if you'd like to join "
                  "or remove yourself from this list!",
      color=discord.Color(0xFF0000)
    )
    embed.set_footer(text="Please select your choice from the preference dropdown below.")
    embed.set_image(url="https://i.imgur.com/SnNqoEl.jpg")
    embed.set_thumbnail(url=f"attachment://dtd.png")

    return embed, thumbnail

def db_get_current_xp_enabled_value(user_id):
  with AgimusDB(dictionary=True) as query:
    sql = "SELECT xp_enabled FROM users WHERE discord_id = %s"
    vals = (user_id,)
    query.execute(sql, vals)
    row = query.fetchone()
  return row['xp_enabled']

def db_toggle_xp(user_id, value:bool):
  with AgimusDB() as query:
    sql = "UPDATE users SET xp_enabled = %s WHERE discord_id = %s"
    vals = (value, user_id)
    query.execute(sql, vals)  

def db_toggle_notifications(user_id, toggle):
  with AgimusDB(dictionary=True) as query:
    sql = "UPDATE users SET receive_notifications = %s WHERE discord_id = %s"
    vals = (toggle, user_id)
    query.execute(sql, vals)
  
def db_toggle_wordcloud(user_id, toggle):
  deleted_row_count = None
  with AgimusDB(dictionary=True) as query:
    sql = "UPDATE users SET log_messages = %s WHERE discord_id = %s"
    vals = (toggle, user_id)
    query.execute(sql, vals)
    if not toggle:
      sql = "DELETE FROM message_history WHERE user_discord_id = %s"
      vals = (user_id,)
      query.execute(sql, vals)
      deleted_row_count = query.rowcount
  return deleted_row_count

def db_toggle_loudbot(user_id, toggle):
  deleted_row_count = None
  with AgimusDB(dictionary=True) as query:
    sql = "UPDATE users SET loudbot_enabled = %s WHERE discord_id = %s"
    vals = (toggle, user_id)
    query.execute(sql, vals)
    if not toggle:
      sql = "DELETE FROM shouts WHERE user_discord_id = %s"
      vals = (user_id,)
      query.execute(sql, vals)
      deleted_row_count = query.rowcount
  return deleted_row_count

def db_add_user_to_dtd(user_id):
  with AgimusDB() as query:
    sql = "SELECT user_discord_id FROM down_to_dabo WHERE user_discord_id = %s"
    vals = (user_id)
    result = query.execute(sql, vals)
    user_already_added = query.fetchone()
    if user_already_added is not None:
      sql = "UPDATE down_to_dabo SET wei"
    sql = "INSERT INTO down_to_dabo (user_discord_id, weight) VALUES (%s, %s)"
    vals = (user_id, 1)
    query.execute(sql, vals)

def db_remove_user_from_dtd(user_id):
  with AgimusDB() as query:
    sql = "DELETE FROM down_to_dabo WHERE user_discord_id = %s"
    vals = (user_id,)
    query.execute(sql, vals)
