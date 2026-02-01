from common import *


THUMBNAIL_URLS = {
  'home': 'https://i.imgur.com/u8W6emy.png',
  'xp': 'https://i.imgur.com/3Wi4fuG.png',
  'notifications': 'https://i.imgur.com/IEaUbsT.png',
  'crystallization': 'https://i.imgur.com/BRKMvb0.png',
  'wordcloud': 'https://i.imgur.com/qg1yqti.png',
  'loudbot': 'https://i.imgur.com/UMHNGHr.png',
  'tagging': 'https://i.imgur.com/9hduiwO.png',
  'pattern_buffer': 'https://i.imgur.com/tRWGRyN.png',
}


SETTINGS_CATEGORIES = [
  ('Home', 'Settings Homepage and Help', 'home'),
  ('XP', 'Opt-in or Opt-out of the XP System', 'xp'),
  ('Notifications', 'Enable or Disable DMs from AGIMUS', 'notifications'),
  ('Crystallization', 'Configure Crystal Auto-Harmonization Behavior', 'crystallization'),
  ('Wordcloud', 'Enable or Disable Wordcloud Logging', 'wordcloud'),
  ('Loudbot', 'Enable or Disable Loudbot Auto-Responses and Logging', 'loudbot'),
  ('User Tagging', 'Opt-in or Opt-out of User Tagging', 'tagging'),
  ('Crystal Pattern Buffer DMs', 'Opt-in or Opt-out of Crystal Pattern Buffer DMs', 'pattern_buffer'),
]


class SettingsCategoryDropdown(discord.ui.Select):
  def __init__(self, view: 'SettingsView', *, selected_key: str):
    self.view = view

    options = []
    for label, desc, key in SETTINGS_CATEGORIES:
      options.append(discord.SelectOption(
        label=label,
        description=desc,
        value=key,
        default=(key == selected_key)
      ))

    super().__init__(
      placeholder='Navigate To Setting',
      min_values=1,
      max_values=1,
      options=options,
      row=0
    )

  async def callback(self, interaction: discord.Interaction):
    await self.view.set_category(interaction, self.values[0])


class SettingsActionDropdown(discord.ui.Select):
  def __init__(self, view: 'SettingsView', *, key: str):
    self.view = view
    self.key = key

    options, placeholder = view.get_action_config_for(key)

    super().__init__(
      placeholder=placeholder,
      min_values=1,
      max_values=1,
      options=options,
      row=1
    )

  async def callback(self, interaction: discord.Interaction):
    await self.view.apply_setting(interaction, self.key, self.values[0])


class SettingsCloseButton(discord.ui.Button):
  def __init__(self, view: 'SettingsView'):
    super().__init__(
      label='Close',
      style=discord.ButtonStyle.secondary,
      row=2
    )
    self.view_ref = view

  async def callback(self, interaction: discord.Interaction):
    try:
      await interaction.response.defer()
    except Exception:
      pass

    try:
      await interaction.message.delete()
    except discord.errors.NotFound:
      pass


class SettingsView(discord.ui.View):
  def __init__(self, cog: commands.Cog, user_id: str):
    super().__init__(timeout=360)
    self.cog = cog
    self.user_id = user_id
    self.category = 'home'
    self.message = None

    self._rebuild_category_control()
    self._rebuild_action_control()
    self.add_item(SettingsCloseButton(self))

  def _rebuild_category_control(self):
    for child in list(self.children):
      if isinstance(child, SettingsCategoryDropdown):
        self.remove_item(child)

    self.add_item(SettingsCategoryDropdown(self, selected_key=self.category))

  def _rebuild_action_control(self):
    for child in list(self.children):
      if isinstance(child, SettingsActionDropdown):
        self.remove_item(child)

    if self.category != 'home':
      self.add_item(SettingsActionDropdown(self, key=self.category))

  def get_action_config_for(self, key: str) -> tuple[list[discord.SelectOption], str]:
    if key == 'xp':
      return ([
        discord.SelectOption(label='Enable XP', description='Opt-in to the XP and Badge System'),
        discord.SelectOption(label='Disable XP', description='Opt-out of the XP and Badge System'),
      ], 'Choose your preference')

    if key == 'notifications':
      return ([
        discord.SelectOption(label='Enable Notifications', description='Allow AGIMUS to send you DMs'),
        discord.SelectOption(label='Disable Notifications', description='Prevent AGIMUS from sending you DMs'),
      ], 'Choose your preference')

    if key == 'crystallization':
      return ([
        discord.SelectOption(label='Auto-Harmonize', description='Automatically Harmonize upon Attunement.'),
        discord.SelectOption(label='Manual', description='Manually Harmonize after Attunement.'),
      ], 'Choose your Crystallization behavior')

    if key == 'wordcloud':
      return ([
        discord.SelectOption(label='Enable Wordcloud', description='Allow logging.'),
        discord.SelectOption(label='Disable Wordcloud', description='Disable logging. NOTE: This also clears your current logs!'),
      ], 'Choose your preference')

    if key == 'loudbot':
      return ([
        discord.SelectOption(label='Enable Loudbot', description='Allow Loudbot auto-responses and log messages.'),
        discord.SelectOption(label='Disable Loudbot', description='Disable Loudbot and clear existing logged messages.'),
      ], 'Choose your preference')

    if key == 'tagging':
      return ([
        discord.SelectOption(label='Enable Tagging', description='Opt-in to the User Tagging System'),
        discord.SelectOption(label='Disable Tagging', description='Opt-out of the User Tagging System'),
      ], 'Choose your preference')

    if key == 'pattern_buffer':
      return ([
        discord.SelectOption(label='Enable Pattern Buffer DM', description='Opt-in to the Pattern Buffer DM'),
        discord.SelectOption(label='Disable Pattern Buffer DM', description='Opt-out of the Pattern Buffer DM'),
      ], 'Choose your preference')

    return ([], 'Choose your preference')

  async def set_category(self, interaction: discord.Interaction, category: str):
    self.category = category
    self._rebuild_category_control()
    self._rebuild_action_control()

    page_embed = await self.cog._build_settings_embed(category)

    await interaction.response.edit_message(embeds=[page_embed], view=self)

  async def apply_setting(self, interaction: discord.Interaction, key: str, selection: str):
    user_id = str(interaction.user.id)
    confirm_embed = None

    if key == 'xp':
      if selection == 'Enable XP':
        await db_toggle_xp(user_id, True)
        confirm_embed = discord.Embed(
          title='You have successfully chosen to participate in the XP and Badge System.',
          color=discord.Color.green()
        ).set_footer(text='You can always come back to this interface to reconfigure in the future!')
      else:
        await db_toggle_xp(user_id, False)
        confirm_embed = discord.Embed(
          title='You have successfully opted-out of the XP and Badge System.',
          color=discord.Color.blurple()
        ).set_footer(text='You can always come back to this interface and re-enable in the future!')

    elif key == 'notifications':
      if selection == 'Enable Notifications':
        await db_toggle_notifications(user_id, True)
        confirm_embed = discord.Embed(
          title='You have successfully allowed AGIMUS to send you DMs.',
          color=discord.Color.green()
        ).set_footer(text='You can always come back to this interface and reconfigure in the future!')
      else:
        await db_toggle_notifications(user_id, False)
        confirm_embed = discord.Embed(
          title='You have successfully disabled AGIMUS from sending you DMs.',
          color=discord.Color.blurple()
        ).set_footer(text='You can always come back to this interface and re-enable in the future!')

    elif key == 'crystallization':
      selection_map = {
        'Auto-Harmonize': True,
        'Manual': False
      }
      await db_set_crystal_autoharmonize(user_id, selection_map[selection])
      confirm_embed = discord.Embed(
        title=f"Crystallization Auto-Harmonize behavior set to '{selection}'.",
        color=discord.Color.green()
      ).set_footer(text='You can always come back to this interface and change this in the future!')

    elif key == 'wordcloud':
      if selection == 'Enable Wordcloud':
        await db_toggle_wordcloud(user_id, True)
        confirm_embed = discord.Embed(
          title='You have successfully allowed AGIMUS to log your common words for the purpose of generating Wordclouds.',
          color=discord.Color.green()
        ).set_footer(text='You can always come back to this interface and reconfigure in the future!')
      else:
        deleted_message_count = await db_toggle_wordcloud(user_id, False)
        confirm_embed = discord.Embed(
          title=f"You have successfully disabled AGIMUS from logging your common words and cleared any current data ({deleted_message_count} messages deleted).",
          color=discord.Color.blurple()
        ).set_footer(text='You can always come back to this interface and re-enable in the future!')

    elif key == 'loudbot':
      if selection == 'Enable Loudbot':
        await db_toggle_loudbot(user_id, True)
        confirm_embed = discord.Embed(
          title='You have successfully allowed AGIMUS to auto-respond to your all-caps messages and log them for parroting in the future.',
          color=discord.Color.green()
        ).set_footer(text='You can always come back to this interface and reconfigure in the future!')
      else:
        deleted_message_count = await db_toggle_loudbot(user_id, False)
        confirm_embed = discord.Embed(
          title=f"You have successfully disabled AGIMUS auto-responding to your all-caps messages and logging messages for the purpose of parroting them in the future. Cleared {deleted_message_count} messages.",
          color=discord.Color.blurple()
        ).set_footer(text='You can always come back to this interface and re-enable in the future!')

    elif key == 'tagging':
      if selection == 'Enable Tagging':
        await db_toggle_tagging(user_id, True)
        confirm_embed = discord.Embed(
          title='You have successfully chosen to participate in user tagging!',
          color=discord.Color.green()
        ).set_footer(text='You can always come back to this interface to reconfigure in the future!')
      else:
        await db_toggle_tagging(user_id, False)
        confirm_embed = discord.Embed(
          title='You have successfully opted-out of being user tagged.',
          color=discord.Color.blurple()
        ).set_footer(text='You can always come back to this interface and re-enable in the future!')

    elif key == 'pattern_buffer':
      if selection == 'Enable Pattern Buffer DM':
        await db_toggle_pattern_buffer(user_id, True)
        confirm_embed = discord.Embed(
          title='You have successfully opted-in to pattern buffer DMs!',
          color=discord.Color.green()
        ).set_footer(text='You can always come back to this interface to reconfigure in the future!')
      else:
        await db_toggle_pattern_buffer(user_id, False)
        confirm_embed = discord.Embed(
          title='You have successfully opted-out of pattern buffer DMs.',
          color=discord.Color.blurple()
        ).set_footer(text='You can always come back to this interface and re-enable in the future!')

    page_embed = await self.cog._build_settings_embed(self.category)

    if confirm_embed:
      await interaction.response.edit_message(embeds=[confirm_embed, page_embed], view=self)
    else:
      await interaction.response.edit_message(embeds=[page_embed], view=self)

  async def on_timeout(self):
    for child in self.children:
      child.disabled = True

    if self.message:
      try:
        await self.message.edit(view=self)
      except discord.errors.NotFound:
        pass


class Settings(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @commands.slash_command(
    name='settings',
    description='Configure your AGIMUS settings!'
  )
  async def settings(self, ctx):
    await ctx.defer(ephemeral=True)

    view = SettingsView(self, user_id=str(ctx.author.id))
    embed = await self._build_settings_embed('home')

    msg = await ctx.followup.send(embeds=[embed], view=view, ephemeral=True)
    view.message = msg

  async def _build_settings_embed(self, category: str) -> discord.Embed:
    if category == 'xp':
      return await self._get_xp_embed()
    if category == 'notifications':
      return await self._get_notifications_embed()
    if category == 'crystallization':
      return await self._get_crystallization_embed()
    if category == 'wordcloud':
      return await self._get_wordcloud_embed()
    if category == 'loudbot':
      return await self._get_loudbot_embed()
    if category == 'tagging':
      return await self._get_tagging_embed()
    if category == 'pattern_buffer':
      return await self._get_pattern_buffer_embed()
    return await self._get_home_embed()

  async def _get_home_embed(self) -> discord.Embed:
    embed = discord.Embed(
      title='Settings',
      description=(
        "AGIMUS is The USS Hood's resident Self-Aware Megalomaniacal Computer and our Discord Bot! "
        'It has a ton of useful functionality and has some user preferences you can configure for features '
        'you may or may not be interested in.\n\n'
        'For more details on what AGIMUS can do, try using `/help` in any channel.'
      ),
      color=discord.Color(0xFF0000)
    )
    embed.set_footer(text='Please use the dropdown below to select a category and begin.')
    embed.set_image(url='https://i.imgur.com/TfDEuSS.jpg')
    embed.set_thumbnail(url=THUMBNAIL_URLS['home'])
    return embed

  async def _get_xp_embed(self) -> discord.Embed:
    badge_channel = await self.bot.fetch_channel(get_channel_id('badgeys-badges'))

    embed = discord.Embed(
      title='XP System Preferences',
      description=(
        'The XP System on the USS Hood awards users XP for participating in the server in various ways. '
        "Some of these include posting messages, reacting to messages, and receiving reactions to your own messages.\n\n"
        "Once you've received a set amount of XP, you will Level Up and receive a new Badge with a notification in "
        f"{badge_channel.mention}. You can start typing `/badges` to see the various badge-specific commands available "
        'for taking a look at your collection!\n\n'
        "If you don't wish to participate, you can configure that here. You can always re-enable if desired in the future!"
      ),
      color=discord.Color(0xFF0000)
    )
    embed.set_footer(text='Please select your choice from the preference dropdown below.')
    embed.set_image(url='https://i.imgur.com/upuEFlq.png')
    embed.set_thumbnail(url=THUMBNAIL_URLS['xp'])
    return embed

  async def _get_crystallization_embed(self) -> discord.Embed:
    embed = discord.Embed(
      title='Crystallization Auto-Harmonize Preference',
      description=(
        "Set how you'd prefer AGIMUS to handle Harmonization (activation) of Crystals after you have Attuned (attached) "
        'them to a Badge via `/crystals attach`.\n\n'
        '* **Auto-Harmonize** - As soon as you attune a Crystal to a Badge, it will become Harmonized immediately!\n'
        "* **Manual** - Don't immediately Harmonize the latest attuned Crystal, use `/crystals activate` to select as per usual (Default).\n\n"
        'Note: If you have multiple Crystals attached to a Badge you can always change which is Harmonized at any time per-usual via `/crystals activate`!'
      ),
      color=discord.Color(0xFF0000)
    )
    embed.set_footer(text='Please select your choice from the dropdown below.')
    embed.set_image(url='https://i.imgur.com/Kkwa9ub.png')
    embed.set_thumbnail(url=THUMBNAIL_URLS['crystallization'])
    return embed

  async def _get_notifications_embed(self) -> discord.Embed:
    embed = discord.Embed(
      title='AGIMUS Notifications',
      description=(
        'AGIMUS may occasionally want to send you a Direct Message with useful information.\n\n'
        'Some examples include sending Drops/Clips lists when requested and notably, DMs are used in the Badge Trading System '
        'to give alerts when a trade has been initiated or one of your existing trades has been canceled.'
      ),
      color=discord.Color(0xFF0000)
    )
    embed.set_footer(text='Please select your choice from the preference dropdown below.')
    embed.set_image(url='https://i.imgur.com/XMnho37.png')
    embed.set_thumbnail(url=THUMBNAIL_URLS['notifications'])
    return embed

  async def _get_wordcloud_embed(self) -> discord.Embed:
    wordcloud_blocked_channel_ids = get_channel_ids_list([
      'neelixs-morale-office',
      'plasma-vent',
      'counselor-trois-waiting-room',
      'heuristic-associative-pathways',
      'megalomaniacal-computer-storage',
      'bot-setup',
      'the-royale',
      'poker-night',
      'morns-nonstop-quiz',
      'badgeys-badges'
    ])
    wordcloud_blocked_channels = [
      await self.bot.fetch_channel(channel_id) for channel_id in wordcloud_blocked_channel_ids
    ]

    wordcloud_blocked_channels_string = '\n\n'
    for channel in wordcloud_blocked_channels:
      wordcloud_blocked_channels_string += f"{channel.mention}\n"

    embed = discord.Embed(
      title='Wordcloud Logging',
      description=(
        'AGIMUS has an opt-in Wordcloud feature which you can enable to track the most common words that you use. '
        'When the command is executed with `/wordcloud` a new image is generated which weighs each word based on frequency.\n\n'
        'If wish to opt out in the future, your existing message data will be deleted.\n\n'
        'Note that the following channels are not included in logging for the Wordcloud: '
        f"{wordcloud_blocked_channels_string}\n**Example Wordcloud:**"
      ),
      color=discord.Color(0xFF0000)
    )
    embed.set_footer(text='Please select your choice from the preference dropdown below.')
    embed.set_image(url='https://i.imgur.com/xNeoDSD.png')
    embed.set_thumbnail(url=THUMBNAIL_URLS['wordcloud'])
    return embed

  async def _get_loudbot_embed(self) -> discord.Embed:
    loudbot_enabled_channel_ids = get_channel_ids_list([
      'after-dinner-conversation',
      'badgeys-badges',
      'bahrats-bazaar',
      'the-royale',
      'dr-crushers-hotbox',
      'megalomaniacal-computer-storage',
      'morns-nonstop-quiz',
      'poker-night',
      'seskas-catfishing-channel',
      'ten-forward',
      'temba-his-arms-wide'
    ])
    loudbot_enabled_channels = [
      await self.bot.fetch_channel(channel_id) for channel_id in loudbot_enabled_channel_ids
    ]

    loudbot_enabled_channels_string = '\n\n'
    for channel in loudbot_enabled_channels:
      loudbot_enabled_channels_string += f"{channel.mention}\n"

    embed = discord.Embed(
      title='Loudbot Auto-Responses and Logging',
      description=(
        'AGIMUS has an opt-in Loudbot feature which you can enable to allow to have it auto-respond to messages you post that are in all-caps. '
        'When your message is registered it also logs the message to be used as a response to other users who have the feature enabled.\n\n'
        'If wish to opt out in the future, your existing message data will be deleted.\n\n'
        f'Note that the following channels are where Loudbot is allowed to auto-respond: {loudbot_enabled_channels_string}'
      ),
      color=discord.Color(0xFF0000)
    )
    embed.set_footer(text='Please select your choice from the preference dropdown below.')
    embed.set_image(url='https://i.imgur.com/wq34YDD.png')
    embed.set_thumbnail(url=THUMBNAIL_URLS['loudbot'])
    return embed

  async def _get_tagging_embed(self) -> discord.Embed:
    embed = discord.Embed(
      title='User Tagging',
      description=(
        'We have an opt-in User Tagging feature which allows FoDs to tag one another with nicknames and other info!\n\n'
        '* `/user_tags tag` - Add a tag to a user.\n'
        "* `/user_tags untag` - Remove a tag that you've been tagged with.\n"
        '* `/user_tags display` - View all tags a user has been tagged with (Posted publicly or privately).\n\n'
        'Select below if you would like to join enable others to tag you (or add some of your own to yourself)!'
      ),
      color=discord.Color(0xFF0000)
    )
    embed.set_footer(text='Please select your choice from the preference dropdown below.')
    embed.set_image(url='https://i.imgur.com/TVAmmjk.jpeg')
    embed.set_thumbnail(url=THUMBNAIL_URLS['tagging'])
    return embed

  async def _get_pattern_buffer_embed(self) -> discord.Embed:
    embed = discord.Embed(
      title='Crystal Pattern Buffer Notifications',
      description=(
        'Crystal Pattern Buffers are rewards given by the XP System. This setting will only apply if you have enabled the XP System. '
        'Opt in if you would like to receive a notification when you receive a Crystal Pattern Buffer.\n\n'
        'Note that this setting only applies to notifications about Crystal Pattern Buffers. If you would like to receive other notifications, '
        'please use the "Notifications" setting.'
      ),
      color=discord.Color(0xFF0000)
    )
    embed.set_footer(text='Please select your choice from the preference dropdown below.')
    embed.set_image(url='https://i.imgur.com/XMnho37.png')
    embed.set_thumbnail(url=THUMBNAIL_URLS['pattern_buffer'])
    return embed


async def db_toggle_xp(user_id, value: bool):
  sql = 'UPDATE users SET xp_enabled = %s WHERE discord_id = %s'
  vals = (value, user_id)
  async with AgimusDB() as db:
    await db.execute(sql, vals)


async def db_toggle_tagging(user_id, value: bool):
  sql = 'UPDATE users SET tagging_enabled = %s WHERE discord_id = %s'
  vals = (value, user_id)
  async with AgimusDB() as db:
    await db.execute(sql, vals)


async def db_toggle_notifications(user_id, toggle):
  sql = 'UPDATE users SET receive_notifications = %s WHERE discord_id = %s'
  vals = (toggle, user_id)
  async with AgimusDB() as db:
    await db.execute(sql, vals)


async def db_toggle_wordcloud(user_id, toggle):
  deleted_row_count = None
  async with AgimusDB() as db:
    sql = 'UPDATE users SET log_messages = %s WHERE discord_id = %s'
    vals = (toggle, user_id)
    await db.execute(sql, vals)

    if not toggle:
      sql = 'DELETE FROM message_history WHERE user_discord_id = %s'
      vals = (user_id,)
      await db.execute(sql, vals)
      deleted_row_count = db.rowcount

  return deleted_row_count


async def db_toggle_loudbot(user_id, toggle):
  deleted_row_count = None
  async with AgimusDB() as db:
    sql = 'UPDATE users SET loudbot_enabled = %s WHERE discord_id = %s'
    vals = (toggle, user_id)
    await db.execute(sql, vals)

    if not toggle:
      sql = 'DELETE FROM shouts WHERE user_discord_id = %s'
      vals = (user_id,)
      await db.execute(sql, vals)
      deleted_row_count = db.rowcount

  return deleted_row_count


async def db_set_crystal_autoharmonize(user_id, autoharmonize: bool):
  sql = 'UPDATE users SET crystal_autoharmonize = %s WHERE discord_id = %s'
  vals = (autoharmonize, user_id)
  async with AgimusDB() as db:
    await db.execute(sql, vals)


async def db_toggle_pattern_buffer(user_id, toggle):
  sql = 'UPDATE users SET pattern_buffer = %s WHERE discord_id = %s'
  vals = (toggle, user_id)
  async with AgimusDB() as db:
    await db.execute(sql, vals)
