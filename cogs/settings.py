from common import *


CATEGORY_MEDIA_URLS = {
  "home": "https://i.imgur.com/TfDEuSS.jpg",
  "xp": "https://i.imgur.com/upuEFlq.png",
  "notifications": "https://i.imgur.com/XMnho37.png",
  "crystallization": "https://i.imgur.com/Kkwa9ub.png",
  "wordcloud": "https://i.imgur.com/xNeoDSD.png",
  "loudbot": "https://i.imgur.com/wq34YDD.png",
  "tagging": "https://i.imgur.com/TVAmmjk.jpeg",
  "pattern_buffer": "https://i.imgur.com/XMnho37.png",
}


SETTINGS_CATEGORIES = [
  ("Home", "Settings Homepage and Help", "home"),
  ("XP", "Opt-in or Opt-out of the XP System", "xp"),
  ("Notifications", "Enable or Disable DMs from AGIMUS", "notifications"),
  ("Crystallization", "Configure Crystal Auto-Harmonization Behavior", "crystallization"),
  ("Wordcloud", "Enable or Disable Wordcloud Logging", "wordcloud"),
  ("Loudbot", "Enable or Disable Loudbot Auto-Responses and Logging", "loudbot"),
  ("User Tagging", "Opt-in or Opt-out of User Tagging", "tagging"),
  ("Crystal Pattern Buffer DMs", "Opt-in or Opt-out of Crystal Pattern Buffer DMs", "pattern_buffer"),
]


CATEGORY_TEXT = {
  "home": {
    "title": "Settings",
    "body": (
      "AGIMUS is The USS Hood's resident Self-Aware Megalomaniacal Computer and our Discord Bot! "
      "It has a ton of useful functionality and has some user preferences you can configure for features "
      "you may or may not be interested in.\n\n"
      "For more details on what AGIMUS can do, try using `/help` in any channel."
    ),
    "footer": "Use the dropdown below to select a category and begin."
  },
  "xp": {
    "title": "XP System Preferences",
    "body": (
      "The XP System on the USS Hood awards users XP for participating in the server in various ways. "
      "Some of these include posting messages, reacting to messages, and receiving reactions to your own messages.\n\n"
      "Once you've received a set amount of XP, you will Level Up and receive a new Badge with a notification in "
      "{badge_channel_mention}. You can start typing `/badges` to see the various badge-specific commands available "
      "for taking a look at your collection.\n\n"
      "If you do not wish to participate, you can configure that here. You can always re-enable if desired in the future."
    ),
    "footer": "Select your preference below."
  },
  "notifications": {
    "title": "AGIMUS Notifications",
    "body": (
      "AGIMUS may occasionally want to send you a Direct Message with useful information.\n\n"
      "Some examples include sending Drops/Clips lists when requested and notably, DMs are used in the Badge Trading System "
      "to give alerts when a trade has been initiated or one of your existing trades has been canceled."
    ),
    "footer": "Select your preference below."
  },
  "crystallization": {
    "title": "Crystallization Auto-Harmonize Preference",
    "body": (
      "Set how you'd prefer AGIMUS to handle Harmonization (activation) of Crystals after you have Attuned (attached) "
      "them to a Badge via `/crystals attach`.\n\n"
      "* **Auto-Harmonize:** As soon as you attune a Crystal to a Badge, it will become Harmonized immediately.\n"
      "* **Manual:** Do not immediately Harmonize the latest attuned Crystal. Use `/crystals activate` to select as per usual.\n\n"
      "If you have multiple Crystals attached to a Badge you can always change which is Harmonized at any time via `/crystals activate`."
    ),
    "footer": "Select your preference below."
  },
  "wordcloud": {
    "title": "Wordcloud Logging",
    "body": (
      "AGIMUS has an opt-in Wordcloud feature which you can enable to track the most common words that you use. "
      "When the command is executed with `/wordcloud` a new image is generated which weighs each word based on frequency.\n\n"
      "If you opt out in the future, your existing message data will be deleted."
    ),
    "footer": "Select your preference below."
  },
  "loudbot": {
    "title": "Loudbot Auto-Responses and Logging",
    "body": (
      "AGIMUS has an opt-in Loudbot feature which you can enable to allow it to auto-respond to messages you post that are in all-caps. "
      "When your message is registered it also logs the message to be used as a response to other users who have the feature enabled.\n\n"
      "If you opt out in the future, your existing message data will be deleted."
    ),
    "footer": "Select your preference below."
  },
  "tagging": {
    "title": "User Tagging",
    "body": (
      "We have an opt-in User Tagging feature which allows FoDs to tag one another with nicknames and other info.\n\n"
      "* `/user_tags tag` - Add a tag to a user\n"
      "* `/user_tags untag` - Remove a tag that you've been tagged with\n"
      "* `/user_tags display` - View all tags a user has been tagged with\n\n"
      "Select below if you would like to enable others to tag you (or add some of your own to yourself)."
    ),
    "footer": "Select your preference below."
  },
  "pattern_buffer": {
    "title": "Crystal Pattern Buffer Notifications",
    "body": (
      "Crystal Pattern Buffers are rewards given by the XP System. This setting will only apply if you have enabled the XP System. "
      "Opt in if you would like to receive a notification when you receive a Crystal Pattern Buffer.\n\n"
      "This setting only applies to notifications about Crystal Pattern Buffers. If you would like to receive other notifications, "
      "please use the Notifications setting."
    ),
    "footer": "Select your preference below."
  }
}


STATUS_THUMBNAILS = {
  "enabled": "https://i.imgur.com/pvgplY9.png",
  "disabled": "https://i.imgur.com/FFlJc9A.png",
}


def _is_enabled_for_category(user_details: dict, category: str) -> bool | None:
  if category == "xp":
    return bool(user_details.get("xp_enabled"))
  if category == "notifications":
    return bool(user_details.get("receive_notifications"))
  if category == "crystallization":
    val = user_details.get("crystal_autoharmonize")
    if val is None:
      return None
    return bool(val)
  if category == "wordcloud":
    return bool(user_details.get("log_messages"))
  if category == "loudbot":
    return bool(user_details.get("loudbot_enabled"))
  if category == "tagging":
    return bool(user_details.get("tagging_enabled"))
  if category == "pattern_buffer":
    return bool(user_details.get("pattern_buffer"))
  return None


class SettingsCategoryDropdown(discord.ui.Select):
  def __init__(self, view: "SettingsView", *, selected_key: str, disabled: bool):
    self.settings_view = view

    options = []
    for label, desc, key in SETTINGS_CATEGORIES:
      options.append(discord.SelectOption(
        label=label,
        description=desc,
        value=key,
        default=(key == selected_key)
      ))

    super().__init__(
      placeholder="Navigate To Setting",
      min_values=1,
      max_values=1,
      options=options,
      disabled=disabled
    )

  async def callback(self, interaction: discord.Interaction):
    await self.settings_view.set_category(interaction, self.values[0])


class SettingsActionDropdown(discord.ui.Select):
  def __init__(self, view: "SettingsView", *, key: str, disabled: bool):
    self.settings_view = view
    self.key = key

    options, placeholder = view.get_action_config_for(key)

    super().__init__(
      placeholder=placeholder,
      min_values=1,
      max_values=1,
      options=options,
      disabled=disabled
    )

  async def callback(self, interaction: discord.Interaction):
    await self.settings_view.apply_setting(interaction, self.key, self.values[0])


class SettingsCloseButton(discord.ui.Button):
  def __init__(self, view: "SettingsView"):
    self.settings_view = view
    super().__init__(label="Close", style=discord.ButtonStyle.secondary)

  async def callback(self, interaction: discord.Interaction):
    ok = await self.settings_view._ack_early(interaction)
    if not ok:
      return

    try:
      fn = getattr(interaction, "delete_original_response", None)
      if fn:
        await fn()
        return
    except discord.errors.NotFound:
      return

    try:
      if self.settings_view._message:
        await self.settings_view._message.delete()
    except discord.errors.NotFound:
      pass


class SettingsView(discord.ui.DesignerView):
  def __init__(self, cog: commands.Cog, user: discord.User, user_details: dict):
    super().__init__(timeout=360)

    self.cog = cog
    self.user = user
    self.user_discord_id = str(user.id)

    self.user_details = user_details
    self.category = "home"

    self.note_title = None
    self.note_body = None
    self.note_status = None

    self._interaction_lock = asyncio.Lock()
    self._message = None

    self._busy = False

  def _clear_note(self):
    self.note_title = None
    self.note_body = None
    self.note_status = None

  def _set_note(self, *, title: str, body: str, status: str | None):
    self.note_title = title
    self.note_body = body
    self.note_status = status

  def get_action_config_for(self, key: str) -> tuple[list[discord.SelectOption], str]:
    if key == "xp":
      return ([
        discord.SelectOption(label="Enable XP", description="Opt-in to the XP and Badge System"),
        discord.SelectOption(label="Disable XP", description="Opt-out of the XP and Badge System"),
      ], "Choose your preference")

    if key == "notifications":
      return ([
        discord.SelectOption(label="Enable Notifications", description="Allow AGIMUS to send you DMs"),
        discord.SelectOption(label="Disable Notifications", description="Prevent AGIMUS from sending you DMs"),
      ], "Choose your preference")

    if key == "crystallization":
      return ([
        discord.SelectOption(label="Auto-Harmonize", description="Automatically Harmonize upon Attunement."),
        discord.SelectOption(label="Manual", description="Manually Harmonize after Attunement."),
      ], "Choose your Crystallization behavior")

    if key == "wordcloud":
      return ([
        discord.SelectOption(label="Enable Wordcloud", description="Allow logging."),
        discord.SelectOption(label="Disable Wordcloud", description="Disable logging. NOTE: This also clears your current logs!"),
      ], "Choose your preference")

    if key == "loudbot":
      return ([
        discord.SelectOption(label="Enable Loudbot", description="Allow Loudbot auto-responses and log messages."),
        discord.SelectOption(label="Disable Loudbot", description="Disable Loudbot and clear existing logged messages."),
      ], "Choose your preference")

    if key == "tagging":
      return ([
        discord.SelectOption(label="Enable Tagging", description="Opt-in to the User Tagging System"),
        discord.SelectOption(label="Disable Tagging", description="Opt-out of the User Tagging System"),
      ], "Choose your preference")

    if key == "pattern_buffer":
      return ([
        discord.SelectOption(label="Enable Pattern Buffer DM", description="Opt-in to the Pattern Buffer DM"),
        discord.SelectOption(label="Disable Pattern Buffer DM", description="Opt-out of the Pattern Buffer DM"),
      ], "Choose your preference")

    return ([
      discord.SelectOption(label="No actions available", value="none", description="This screen has no actions.")
    ], "Choose your preference")

  def _set_status_note_for_current_category(self):
    if self.category == "crystallization":
      val = self.user_details.get("crystal_autoharmonize")
      if val is None:
        self._clear_note()
        return

      mode = "Auto-Harmonize" if bool(val) else "Manual"
      thumb = "enabled" if bool(val) else "disabled"
      self._set_note(
        title="Status",
        body=f"This setting is currently set to {mode}.",
        status=thumb
      )
      return

    enabled = _is_enabled_for_category(self.user_details, self.category)
    if enabled is None:
      self._clear_note()
      return

    state_text = "enabled" if enabled else "disabled"
    self._set_note(
      title="Status",
      body=f"This setting is currently {state_text}.",
      status=state_text
    )

  async def on_timeout(self):
    try:
      if self._message:
        await self._message.delete()
    except Exception:
      pass

  def _badge_channel_mention_fast(self) -> str:
    try:
      chan_id = get_channel_id("badgeys-badges")
      chan = self.cog.bot.get_channel(chan_id)
      if chan:
        return chan.mention
    except Exception:
      pass
    return "#badgeys-badges"

  async def _build_container(self) -> discord.ui.Container:
    category_data = CATEGORY_TEXT[self.category]
    title = category_data["title"]
    body = category_data["body"]
    footer = category_data["footer"]

    if self.category == "xp":
      body = body.replace("{badge_channel_mention}", self._badge_channel_mention_fast())

    media_url = CATEGORY_MEDIA_URLS[self.category]

    container = discord.ui.Container(color=discord.Color.red().value)
    container.add_item(discord.ui.TextDisplay(f"# {title}\n{body}"))

    container.add_item(discord.ui.Separator())
    try:
      container.add_gallery(discord.MediaGalleryItem(url=media_url, description=title))
    except Exception:
      container.add_item(discord.ui.TextDisplay(media_url))

    if self.note_title and self.note_body:
      container.add_item(discord.ui.Separator())

      accessory = None
      if self.note_status in ("enabled", "disabled"):
        accessory = discord.ui.Thumbnail(
          url=STATUS_THUMBNAILS[self.note_status],
          description=self.note_status
        )

      note_text = f"### {self.note_title}\n{self.note_body}".strip()
      if accessory:
        container.add_item(discord.ui.Section(discord.ui.TextDisplay(note_text), accessory=accessory))
      else:
        container.add_item(discord.ui.TextDisplay(note_text))

    container.add_item(discord.ui.Separator())

    footer_text = "..." if self._busy else footer
    container.add_item(discord.ui.TextDisplay(f"-# {footer_text}"))

    container.add_item(discord.ui.Separator())

    controls_disabled = bool(self._busy)

    category_row = discord.ui.ActionRow()
    category_row.add_item(SettingsCategoryDropdown(self, selected_key=self.category, disabled=controls_disabled))
    container.add_item(category_row)

    if self.category != "home":
      action_row = discord.ui.ActionRow()
      action_row.add_item(SettingsActionDropdown(self, key=self.category, disabled=controls_disabled))
      container.add_item(action_row)

    close_row = discord.ui.ActionRow()
    close_row.add_item(SettingsCloseButton(self))
    container.add_item(close_row)

    return container

  async def _rebuild_view(self):
    self.clear_items()
    container = await self._build_container()
    self.add_item(container)

  async def _ack_early(self, interaction: discord.Interaction) -> bool:
    if not interaction:
      return False
    if interaction.response.is_done():
      return True

    try:
      try:
        await interaction.response.defer(invisible=True)
      except TypeError:
        await interaction.response.defer()
      return True
    except discord.errors.NotFound:
      return False

  async def _edit_original(self, interaction: discord.Interaction):
    try:
      await interaction.edit_original_response(view=self)
    except discord.errors.NotFound:
      return

  async def render_initial(self):
    self._clear_note()
    self._busy = False
    await self._rebuild_view()

  async def _set_busy(self, interaction: discord.Interaction, busy: bool):
    async with self._interaction_lock:
      self._busy = busy
      await self._rebuild_view()
      await self._edit_original(interaction)

  async def set_category(self, interaction: discord.Interaction, category: str):
    ok = await self._ack_early(interaction)
    if not ok:
      return

    async with self._interaction_lock:
      if self._busy:
        return
      self._busy = True

    await self._rebuild_view()
    await self._edit_original(interaction)

    async with self._interaction_lock:
      self.category = category
      self._clear_note()
      if self.category != "home":
        self._set_status_note_for_current_category()
      self._busy = False

    await self._rebuild_view()
    await self._edit_original(interaction)

  def _kickoff_background_delete(self, *, kind: str, user_id: str):
    async def _runner():
      try:
        if kind == "wordcloud":
          await db_purge_wordcloud_history(user_id)
        elif kind == "loudbot":
          await db_purge_loudbot_shouts(user_id)
      except Exception:
        logger.exception(f"[settings] background_delete:{kind}:{user_id}")

    try:
      asyncio.create_task(_runner())
    except Exception:
      logger.exception(f"[settings] background_delete_create_task:{kind}:{user_id}")

  async def apply_setting(self, interaction: discord.Interaction, key: str, selection: str):
    ok = await self._ack_early(interaction)
    if not ok:
      return

    async with self._interaction_lock:
      if self._busy:
        return
      self._busy = True

    await self._rebuild_view()
    await self._edit_original(interaction)

    user_id = str(interaction.user.id)

    if key == "xp":
      if selection == "Enable XP":
        await db_toggle_xp(user_id, True)
      elif selection == "Disable XP":
        await db_toggle_xp(user_id, False)

    elif key == "notifications":
      if selection == "Enable Notifications":
        await db_toggle_notifications(user_id, True)
      elif selection == "Disable Notifications":
        await db_toggle_notifications(user_id, False)

    elif key == "crystallization":
      selection_map = {
        "Auto-Harmonize": True,
        "Manual": False
      }
      if selection in selection_map:
        await db_set_crystal_autoharmonize(user_id, selection_map[selection])

    elif key == "wordcloud":
      if selection == "Enable Wordcloud":
        await db_toggle_wordcloud_flag(user_id, True)
      elif selection == "Disable Wordcloud":
        await db_toggle_wordcloud_flag(user_id, False)
        self._kickoff_background_delete(kind="wordcloud", user_id=user_id)

    elif key == "loudbot":
      if selection == "Enable Loudbot":
        await db_toggle_loudbot_flag(user_id, True)
      elif selection == "Disable Loudbot":
        await db_toggle_loudbot_flag(user_id, False)
        self._kickoff_background_delete(kind="loudbot", user_id=user_id)

    elif key == "tagging":
      if selection == "Enable Tagging":
        await db_toggle_tagging(user_id, True)
      elif selection == "Disable Tagging":
        await db_toggle_tagging(user_id, False)

    elif key == "pattern_buffer":
      if selection == "Enable Pattern Buffer DM":
        await db_toggle_pattern_buffer(user_id, True)
      elif selection == "Disable Pattern Buffer DM":
        await db_toggle_pattern_buffer(user_id, False)

    self.user_details = await get_user(user_id)

    async with self._interaction_lock:
      self._clear_note()
      if self.category != "home":
        self._set_status_note_for_current_category()
      self._busy = False

    await self._rebuild_view()
    await self._edit_original(interaction)


class Settings(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @commands.slash_command(
    name="settings",
    description="Configure your AGIMUS settings!"
  )
  async def settings(self, ctx: discord.ApplicationContext):
    try:
      await ctx.defer(ephemeral=True)
    except Exception:
      pass

    user_discord_id = str(ctx.user.id)
    user_details = await get_user(user_discord_id)

    view = SettingsView(self, ctx.user, user_details)
    await view.render_initial()

    msg = await ctx.followup.send(view=view, ephemeral=True)
    view._message = msg


async def db_toggle_xp(user_id: str, value: bool):
  sql = "UPDATE users SET xp_enabled = %s WHERE discord_id = %s"
  vals = (value, user_id)
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, vals)


async def db_toggle_tagging(user_id: str, value: bool):
  sql = "UPDATE users SET tagging_enabled = %s WHERE discord_id = %s"
  vals = (value, user_id)
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, vals)


async def db_toggle_notifications(user_id: str, toggle: bool):
  sql = "UPDATE users SET receive_notifications = %s WHERE discord_id = %s"
  vals = (toggle, user_id)
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, vals)


async def db_toggle_wordcloud_flag(user_id: str, toggle: bool):
  sql = "UPDATE users SET log_messages = %s WHERE discord_id = %s"
  vals = (toggle, user_id)
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, vals)


async def db_purge_wordcloud_history(user_id: str):
  sql = "DELETE FROM message_history WHERE user_discord_id = %s"
  vals = (user_id,)
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, vals)


async def db_toggle_loudbot_flag(user_id: str, toggle: bool):
  sql = "UPDATE users SET loudbot_enabled = %s WHERE discord_id = %s"
  vals = (toggle, user_id)
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, vals)


async def db_purge_loudbot_shouts(user_id: str):
  sql = "DELETE FROM shouts WHERE user_discord_id = %s"
  vals = (user_id,)
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, vals)


async def db_set_crystal_autoharmonize(user_id: str, autoharmonize: bool):
  sql = "UPDATE users SET crystal_autoharmonize = %s WHERE discord_id = %s"
  vals = (autoharmonize, user_id)
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, vals)


async def db_toggle_pattern_buffer(user_id: str, toggle: bool):
  sql = "UPDATE users SET pattern_buffer = %s WHERE discord_id = %s"
  vals = (toggle, user_id)
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, vals)
