from common import *

from queries.trade import *
from queries.echelon_xp import db_get_echelon_progress

from utils.badge_trades import *
from utils.check_channel_access import access_check
from utils.image_utils import *
from utils.prestige import PRESTIGE_TIERS, autocomplete_prestige_tiers, is_prestige_valid
from utils.string_utils import strip_bullshit

from random import sample

f = open("./data/rules_of_acquisition.txt", "r")
data = f.read()
rules_of_acquisition = data.split("\n")
f.close()

# cogs.trade

#    _____          __                                     .__          __
#   /  _  \  __ ___/  |_  ____   ____  ____   _____ ______ |  |   _____/  |_  ____
#  /  /_\  \|  |  \   __\/  _ \_/ ___\/  _ \ /     \\____ \|  | _/ __ \   __\/ __ \
# /    |    \  |  /|  | (  <_> )  \__(  <_> )  Y Y  \  |_> >  |_\  ___/|  | \  ___/
# \____|__  /____/ |__|  \____/ \___  >____/|__|_|  /   __/|____/\___  >__|  \___  >
#         \/                        \/            \/|__|             \/          \/
async def autocomplete_offering_badges(ctx: discord.AutocompleteContext):
  requestor_user_id = ctx.interaction.user.id

  requestee_user_id = None
  prestige_level = None
  offered_instance_ids = set()
  if 'requestee' in ctx.options and 'prestige' in ctx.options:
    requestee_user_id = ctx.options['requestee']
    prestige = ctx.options.get('prestige')
    try:
      prestige_level = int(prestige)
    except ValueError:
      logger.warning(f"Non-numeric prestige level received: {prestige}")
      return [discord.OptionChoice(name="[ 🔒 Invalid Prestige ]", value="none")]
  else:
    active_trade = await db_get_active_requestor_trade(requestor_user_id)
    if active_trade:
      requestee_user_id = active_trade['requestee_id']
      prestige_level = active_trade['prestige_level']
      offered_instances = await db_get_trade_offered_badge_instances(active_trade)
      offered_instance_ids = {b['badge_instance_id'] for b in offered_instances}
    else:
      return [
        discord.OptionChoice(
          name="[ No Valid Options ]",
          value=None
        )
      ]

  # Lookup badges
  requestor_instances = await db_get_user_badge_instances(requestor_user_id, prestige=prestige_level)
  requestee_instances = await db_get_user_badge_instances(requestee_user_id, prestige=prestige_level)

  requestee_filenames = {b['badge_filename'] for b in requestee_instances}

  results = [
    discord.OptionChoice(
      name=b['badge_name'],
      value=str(b['badge_instance_id'])
    )
    for b in requestor_instances
    if (
      not b['special'] and
      b['badge_filename'] not in requestee_filenames and
      b['badge_instance_id'] not in offered_instance_ids
    )
  ]

  filtered = [r for r in results if strip_bullshit(ctx.value.lower()) in strip_bullshit(r.name.lower())]
  if not filtered:
    filtered = [
      discord.OptionChoice(
        name="[ No Valid Options ]",
        value=None
      )
    ]
  return filtered


async def autocomplete_requesting_badges(ctx: discord.AutocompleteContext):
  requestor_user_id = ctx.interaction.user.id

  requestee_user_id = None
  prestige_level = None
  requested_instance_ids = set()
  if 'requestee' in ctx.options and 'prestige' in ctx.options:
    requestee_user_id = ctx.options['requestee']
    prestige = ctx.options.get('prestige')
    try:
      prestige_level = int(prestige)
    except ValueError:
      logger.warning(f"Non-numeric prestige level received: {prestige}")
      return [discord.OptionChoice(name="[ 🔒 Invalid Prestige ]", value="none")]
  else:
    active_trade = await db_get_active_requestor_trade(requestor_user_id)
    if active_trade:
      requestee_user_id = active_trade['requestee_id']
      prestige_level = active_trade['prestige_level']
      requested_instances = await db_get_trade_requested_badge_instances(active_trade)
      requested_instance_ids = {b['badge_instance_id'] for b in requested_instances}
    else:
      return [
        discord.OptionChoice(
          name="[ No Valid Options ]",
          value=None
        )
      ]

  # Lookup badges
  requestor_instances = await db_get_user_badge_instances(requestor_user_id, prestige=prestige_level)
  requestee_instances = await db_get_user_badge_instances(requestee_user_id, prestige=prestige_level)

  requestor_filenames = {b['badge_filename'] for b in requestor_instances}

  results = [
    discord.OptionChoice(
      name=b['badge_name'],
      value=str(b['badge_instance_id'])
    )
    for b in requestee_instances
    if (
      not b['special'] and
      b['badge_filename'] not in requestor_filenames and
      b['badge_instance_id'] not in requested_instance_ids
    )
  ]

  filtered = [r for r in results if strip_bullshit(ctx.value.lower()) in strip_bullshit(r.name.lower())]
  if not filtered:
    filtered = [
      discord.OptionChoice(
        name="[ No Valid Options ]",
        value=None
      )
    ]
  return filtered



# ____   ____.__
# \   \ /   /|__| ______  _  ________
#  \   Y   / |  |/ __ \ \/ \/ /  ___/
#   \     /  |  \  ___/\     /\___ \
#    \___/   |__|\___  >\/\_//____  >
#                    \/           \/
class SendButton(discord.ui.Button):
  def __init__(self, cog, active_trade):
    self.cog = cog
    self.active_trade = active_trade
    super().__init__(
      label="      Send      ",
      style=discord.ButtonStyle.green,
      row=2
    )

  async def callback(self, interaction: discord.Interaction):
    await self.cog._send_trade_callback(interaction, self.active_trade)

class CancelButton(discord.ui.Button):
  def __init__(self, cog, active_trade):
    self.cog = cog
    self.active_trade = active_trade
    super().__init__(
      label="   Cancel Trade   ",
      style=discord.ButtonStyle.red,
      row=2
    )

  async def callback(self, interaction:discord.Interaction):
    await self.cog._cancel_trade_callback(interaction, self.active_trade)

class SendCancelView(discord.ui.View):
  def __init__(self, cog, active_trade):
    super().__init__()

    self.add_item(CancelButton(cog, active_trade))
    if active_trade["status"] != 'active':
      self.add_item(SendButton(cog, active_trade))


class RequestsDropDown(discord.ui.Select):
    def __init__(self, cog, requestors):
      self.cog = cog

      options = []
      for user in requestors:
        option = discord.SelectOption(
          label=user.display_name,
          value=f"{user.id}"
        )
        options.append(option)

      super().__init__(
        placeholder="Which incoming request?",
        min_values=1,
        max_values=1,
        options=options,
      )

    async def callback(self, interaction: discord.Interaction):
      # Clear view once selected
      view = self.view
      view.clear_items()
      await interaction.response.edit_message(
        embed=discord.Embed(
          title="Confirmed Selection",
          description="Just a moment while AGIMUS pulls up the request...",
          color=discord.Color.dark_purple()
        ),
        view=view
      )
      # Send the user the trade interface for this request
      requestor = self.values[0]
      await self.cog._send_pending_trade_interface(interaction, requestor)

class Requests(discord.ui.View):
  def __init__(self, cog, requestors):
    super().__init__()
    self.add_item(RequestsDropDown(cog, requestors))


class AcceptButton(discord.ui.Button):
  def __init__(self, cog, active_trade):
    self.cog = cog
    self.active_trade = active_trade
    super().__init__(
      label="     Accept     ",
      style=discord.ButtonStyle.green,
      row=2
    )

  async def callback(self, interaction: discord.Interaction):
    await interaction.response.edit_message(
      embed=discord.Embed(
        title="Trade Initiated",
        description="Just a moment please...",
        color=discord.Color.dark_purple()
      ),
      view=None,
      attachments=[]
    )
    await self.cog._accept_trade_callback(interaction, self.active_trade)

class DeclineButton(discord.ui.Button):
  def __init__(self, cog, active_trade):
    self.cog = cog
    self.active_trade = active_trade
    super().__init__(
      label="     Decline     ",
      style=discord.ButtonStyle.red,
      row=2
    )

  async def callback(self, interaction:discord.Interaction):
    await self.cog._decline_trade_callback(interaction, self.active_trade)

class AcceptDeclineView(discord.ui.View):
  def __init__(self, cog, active_trade):
    super().__init__()
    self.add_item(DeclineButton(cog, active_trade))
    self.add_item(AcceptButton(cog, active_trade))



# ___________                  .___     _________
# \__    ___/___________     __| _/____ \_   ___ \  ____   ____
#   |    |  \_  __ \__  \   / __ |/ __ \/    \  \/ /  _ \ / ___\
#   |    |   |  | \// __ \_/ /_/ \  ___/\     \___(  <_> ) /_/  >
#   |____|   |__|  (____  /\____ |\___  >\______  /\____/\___  /
#                       \/      \/    \/        \/      /_____/
class Trade(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    # We only allow requestees to have n trades pending for managability's sake
    self.max_trades = 10
    self.max_badges_per_trade = 6
    self.trade_buttons = [
      pages.PaginatorButton("prev", label="⬅", style=discord.ButtonStyle.primary, row=1),
      pages.PaginatorButton(
        "page_indicator", style=discord.ButtonStyle.gray, disabled=True, row=1
      ),
      pages.PaginatorButton("next", label="➡", style=discord.ButtonStyle.primary, row=1),
    ]

  trade = discord.SlashCommandGroup("trade", "Commands for trading badges")



  # .___                            .__
  # |   | ____   ____  ____   _____ |__| ____    ____
  # |   |/    \_/ ___\/  _ \ /     \|  |/    \  / ___\
  # |   |   |  \  \__(  <_> )  Y Y  \  |   |  \/ /_/  >
  # |___|___|  /\___  >____/|__|_|  /__|___|  /\___  /
  #          \/     \/            \/        \//_____/
  @trade.command(
    name="incoming",
    description="View and accept/decline incoming trades from other users"
  )
  @commands.check(access_check)
  async def incoming(self, ctx:discord.ApplicationContext):
    incoming_trades = await db_get_active_requestee_trades(ctx.user.id)

    if not incoming_trades:
      await ctx.respond(embed=discord.Embed(
        title="No Incoming Trade Requests",
        description="No one has any active trades requested from you.\n\nGet out there, arrr, start hustlin' me heartie!",
        color=discord.Color.blurple()
      ), ephemeral=True)
      return

    incoming_requestor_ids = [int(t["requestor_id"]) for t in incoming_trades]
    requestors = []
    for user_id in incoming_requestor_ids:
      try:
        member = await self.bot.current_guild.fetch_member(user_id)
        if member:
          requestors.append(member)
      except discord.NotFound:
        logger.warning(f"Could not fetch guild member with ID {user_id} for incoming trade list.")

    if not requestors:
      await ctx.respond(embed=discord.Embed(
        title="Error fetching users",
        description="We couldn't find any of the users who have open trades with you. They may have left the server.",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    view = Requests(self, requestors)

    await ctx.respond(
      embed=discord.Embed(
        title="Incoming Trade Requests",
        description="The users in the dropdown below have requested a trade from you.",
        color=discord.Color.dark_purple()
      ).set_footer(text="Note: Selecting an option may take a few seconds to register."),
      view=view,
      ephemeral=True
    )

  async def _send_pending_trade_interface(self, interaction: discord.Interaction, requestor_id: int):
    requestee_id = interaction.user.id
    active_trade = await db_get_active_trade_between_requestor_and_requestee(requestor_id, requestee_id)

    if not active_trade:
      await interaction.response.send_message(
        embed=discord.Embed(
          title="Trade Not Found",
          description="There doesn't appear to be an active trade between you and this user.",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    trade_pages = await self._generate_trade_pages(active_trade)
    view = AcceptDeclineView(self, active_trade)

    paginator = pages.Paginator(
      pages=trade_pages,
      use_default_buttons=False,
      custom_buttons=self.trade_buttons,
      custom_view=view,
      loop_pages=True,
      disable_on_timeout=False
    )

    await paginator.respond(interaction, ephemeral=True)

  async def _accept_trade_callback(self, interaction, active_trade):
    await self._cancel_invalid_related_trades(active_trade)

    requestor = await self.bot.current_guild.fetch_member(active_trade["requestor_id"])
    requestee = await self.bot.current_guild.fetch_member(active_trade["requestee_id"])
    prestige_tier = PRESTIGE_TIERS[active_trade['prestige_level']]

    offered_instances = await db_get_trade_offered_badge_instances(active_trade)
    requested_instances = await db_get_trade_requested_badge_instances(active_trade)

    offered_names = "\n".join([f"* {b['badge_name']}" for b in offered_instances]) or "None"
    requested_names = "\n".join([f"* {b['badge_name']}" for b in requested_instances]) or "None"

    # Prevent prestige-leak trades
    requestor_echelon_progress = await db_get_echelon_progress(active_trade["requestor_id"])
    requestee_echelon_progress = await db_get_echelon_progress(active_trade["requestee_id"])

    active_trade_prestige = active_trade['prestige_level']

    if requestor_echelon_progress['current_prestige_tier'] < active_trade_prestige:
      await db_cancel_trade(active_trade)
      await interaction.followup.send(embed=discord.Embed(
        title="Invalid Trade",
        description=f"{requestor.display_name} is not eligible to send {PRESTIGE_TIERS[active_trade_prestige]} badges.\n\nTrade Canceled.",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    if requestee_echelon_progress['current_prestige_tier'] < active_trade['prestige_level']:
      await db_cancel_trade(active_trade)
      await interaction.followup.send(embed=discord.Embed(
        title="Invalid Trade",
        description=f"{requestee.display_name} is not eligible to receive {PRESTIGE_TIERS[active_trade_prestige]} badges.\n\nTrade Canceled.",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    # Trade validity failsafes
    if await self._requestor_already_has_badges(interaction, active_trade, requestor, requestee):
      return
    if await self._requestee_already_has_badges(interaction, active_trade, requestor, requestee):
      return
    if not await self._requestor_still_has_badges(interaction, active_trade, requestor, requestee):
      return
    if not await self._requestee_still_has_badges(interaction, active_trade, requestor, requestee):
      return

    # Perform the trade
    await db_perform_badge_transfer(active_trade)
    await db_complete_trade(active_trade)

    # Confirmation embed
    success_embed = discord.Embed(
      title="Successful Trade!",
      description=(
        f"**{requestor.display_name}** and **{requestee.display_name}** came to an {prestige_tier} Trade agreement!\n\n"
        f"{prestige_tier} Badges transferred successfully!"
      ),
      color=discord.Color.dark_purple()
    )
    success_embed.add_field(
      name=f"{requestor.display_name} received",
      value=requested_names
    )
    success_embed.add_field(
      name=f"{requestee.display_name} received",
      value=offered_names
    )
    success_embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
      icon_url="https://i.imgur.com/GTN4gQG.jpg"
    )

    success_image = discord.File(
      fp="./images/trades/assets/trade_successful.jpg",
      filename="trade_successful.jpg"
    )
    success_embed.set_image(url="attachment://trade_successful.jpg")

    message = await interaction.channel.send(embed=success_embed, file=success_image)

    # DM the requestor
    requestor_user = await get_user(requestor.id)
    if requestor_user["receive_notifications"]:
      try:
        success_embed.add_field(
          name="View Confirmation",
          value=message.jump_url,
          inline=False
        )
        success_embed.set_footer(
          text="Note: You can use /settings to enable or disable these messages."
        )
        await requestor.send(embed=success_embed)
      except discord.Forbidden:
        logger.info(f"DMs closed for {requestor.display_name}")


  async def _cancel_invalid_related_trades(self, active_trade):
    # Find all trades affected by badges in this confirmed trade
    related_trades = await db_get_related_badge_instance_trades(active_trade)
    trades_to_cancel = [t for t in related_trades if t["id"] != active_trade["id"]]

    for trade in trades_to_cancel:
      await db_cancel_trade(trade)

      requestor = await self.bot.current_guild.fetch_member(trade['requestor_id'])
      requestee = await self.bot.current_guild.fetch_member(trade['requestee_id'])
      prestige_tier = PRESTIGE_TIERS[trade['prestige_level']]

      offered_badge_names, requested_badge_names = await get_offered_and_requested_badge_names(trade)

      # Notify requestee
      requestee_user = await get_user(requestee.id)
      if trade['status'] == 'active' and requestee_user["receive_notifications"]:
        try:
          embed = discord.Embed(
            title="Trade Canceled",
            description=f"Your USS Hood {prestige_tier} Badge Trade initiated by **{requestor.display_name}** was canceled because one or more badges were traded to someone else.",
            color=discord.Color.purple()
          )
          embed.add_field(name=f"Offered by {requestor.display_name}", value=offered_badge_names)
          embed.add_field(name=f"Requested from {requestee.display_name}", value=requested_badge_names)
          embed.set_footer(text="Note: You can use /settings to enable or disable these messages.")
          await requestee.send(embed=embed)
        except discord.Forbidden:
          logger.info(f"Could not notify {requestee.display_name} — DMs closed.")

      # Notify requestor
      requestor_user = await get_user(requestor.id)
      if requestor_user["receive_notifications"]:
        try:
          embed = discord.Embed(
            title="Trade Canceled",
            description=f"Your USS Hood {prestige_tier} Badge Trade requested from **{requestee.display_name}** was canceled because one or more badges were traded to someone else.",
            color=discord.Color.purple()
          )
          embed.add_field(name=f"Offered by {requestor.display_name}", value=offered_badge_names)
          embed.add_field(name=f"Requested from {requestee.display_name}", value=requested_badge_names)
          embed.set_footer(text="Note: You can use /settings to enable or disable these messages.")
          await requestor.send(embed=embed)
        except discord.Forbidden:
          logger.info(f"Could not notify {requestor.display_name} — DMs closed.")


  async def _requestor_already_has_badges(self, interaction, active_trade, requestor, requestee):
    requestor_instances = await db_get_user_badge_instances(active_trade['requestor_id'], prestige=active_trade['prestige_level'])
    requestor_filenames = {b['badge_filename'] for b in requestor_instances}

    requested_instances = await db_get_trade_requested_badge_instances(active_trade)
    requested_filenames = {b['badge_filename'] for b in requested_instances}

    overlap = requestor_filenames & requested_filenames

    if overlap:
      prestige_tier = PRESTIGE_TIERS[active_trade['prestige_level']]
      await db_cancel_trade(active_trade)
      await interaction.followup.send(
        embed=discord.Embed(
          title=f"Invalid {prestige_tier} Trade",
          description="Sorry! They've already received some of the badges you requested elsewhere while this trade was pending!\n\nTrade has been canceled.",
          color=discord.Color.red()
        ),
        ephemeral=True
      )

      try:
        offered_badge_names, requested_badge_names = await get_offered_and_requested_badge_names(active_trade)

        embed = discord.Embed(
          title="Trade Canceled",
          description=f"Just a heads up! Your USS Hood {prestige_tier} Badge Trade requested from **{requestee.display_name}** was canceled because you already own some of the badges requested!",
          color=discord.Color.purple()
        )
        embed.add_field(
          name=f"Offered by {requestor.display_name}",
          value=offered_badge_names
        )
        embed.add_field(
          name=f"Requested from {requestee.display_name}",
          value=requested_badge_names
        )
        embed.set_footer(
          text="Note: You can use /settings to enable or disable these messages."
        )
        await requestor.send(embed=embed)
      except discord.Forbidden:
        logger.info(f"Unable to send trade cancelation message to {requestor.display_name}, they have their DMs closed.")

      return True

    return False


  async def _requestee_already_has_badges(self, interaction, active_trade, requestor, requestee):
    requestee_instances = await db_get_user_badge_instances(active_trade['requestee_id'], prestige=active_trade['prestige_level'])
    requestee_filenames = {b['badge_filename'] for b in requestee_instances}

    offered_instances = await db_get_trade_offered_badge_instances(active_trade)
    offered_filenames = {b['badge_filename'] for b in offered_instances}

    overlap = requestee_filenames & offered_filenames

    if overlap:
      prestige_tier = PRESTIGE_TIERS[active_trade['prestige_level']]
      await db_cancel_trade(active_trade)
      await interaction.followup.send(
        embed=discord.Embed(
          title=f"Invalid {prestige_tier} Trade",
          description="Sorry! You've already received some of the badges that were offered to you elsewhere while this trade was pending!\n\nTrade has been canceled.",
          color=discord.Color.red()
        ),
        ephemeral=True
      )

      try:
        offered_badge_names, requested_badge_names = await get_offered_and_requested_badge_names(active_trade)

        embed = discord.Embed(
          title="Trade Canceled",
          description=f"Just a heads up! Your USS Hood {prestige_tier} Badge Trade requested from **{requestee.display_name}** was canceled because they already own some of the badges offered!",
          color=discord.Color.purple()
        )
        embed.add_field(
          name=f"Offered by {requestor.display_name}",
          value=offered_badge_names
        )
        embed.add_field(
          name=f"Requested from {requestee.display_name}",
          value=requested_badge_names
        )
        embed.set_footer(
          text="Note: You can use /settings to enable or disable these messages."
        )
        await requestor.send(embed=embed)
      except discord.Forbidden:
        logger.info(f"Unable to send trade cancelation message to {requestor.display_name}, they have their DMs closed.")

      return True

    return False


  async def _requestor_still_has_badges(self, interaction, active_trade, requestor, requestee):
    user_instances = await db_get_user_badge_instances(requestor.id, prestige=active_trade['prestige_level'])
    current_ids = {b['badge_instance_id'] for b in user_instances}

    offered_instances = await db_get_trade_offered_badge_instances(active_trade)
    offered_ids = {b['badge_instance_id'] for b in offered_instances}

    if not offered_ids.issubset(current_ids):
      prestige_tier = PRESTIGE_TIERS[active_trade['prestige_level']]
      await db_cancel_trade(active_trade)
      await interaction.followup.send(
        embed=discord.Embed(
          title=f"Invalid {prestige_tier} Trade",
          description="Sorry! They no longer have some of the badges they offered!\n\nTrade has been canceled.",
          color=discord.Color.red()
        ),
        ephemeral=True
      )

      try:
        offered_names, requested_names = await get_offered_and_requested_badge_names(active_trade)
        embed = discord.Embed(
          title="Trade Canceled",
          description=f"Just a heads up! Your USS Hood {prestige_tier} Badge Trade you requested from **{requestee.display_name}** was canceled because you no longer have some of the badges you offered!",
          color=discord.Color.purple()
        )
        embed.add_field(name=f"Offered by {requestor.display_name}", value=offered_names)
        embed.add_field(name=f"Requested from {requestee.display_name}", value=requested_names)
        embed.set_footer(text="Note: You can use /settings to enable or disable these messages.")
        await requestor.send(embed=embed)
      except discord.Forbidden:
        logger.info(f"Unable to send trade cancelation message to {requestor.display_name}, they have their DMs closed.")

      return False

    return True


  async def _requestee_still_has_badges(self, interaction, active_trade, requestor, requestee):
    user_instances = await db_get_user_badge_instances(requestee.id, prestige=active_trade['prestige_level'])
    current_ids = {b['badge_instance_id'] for b in user_instances}

    requested_instances = await db_get_trade_requested_badge_instances(active_trade)
    requested_ids = {b['badge_instance_id'] for b in requested_instances}

    if not requested_ids.issubset(current_ids):
      prestige_tier = PRESTIGE_TIERS[active_trade['prestige_level']]
      await db_cancel_trade(active_trade)
      await interaction.followup.send(
        embed=discord.Embed(
          title=f"Invalid {prestige_tier} Trade",
          description="Sorry! You no longer have some of the badges they requested!\n\nTrade has been canceled.",
          color=discord.Color.red()
        ),
        ephemeral=True
      )

      try:
        offered_names, requested_names = await get_offered_and_requested_badge_names(active_trade)
        embed = discord.Embed(
          title="Trade Canceled",
          description=f"Just a heads up! Your USS Hood {prestige_tier} Badge Trade requested by **{requestor.display_name}** was canceled because you no longer have some of the badges they requested!",
          color=discord.Color.purple()
        )
        embed.add_field(name=f"Offered by {requestor.display_name}", value=offered_names)
        embed.add_field(name=f"Requested from {requestee.display_name}", value=requested_names)
        embed.set_footer(text="Note: You can use /settings to enable or disable these messages.")
        await requestor.send(embed=embed)
      except discord.Forbidden:
        logger.info(f"Unable to send trade cancelation message to {requestor.display_name}, they have their DMs closed.")

      return False

    return True

  async def _decline_trade_callback(self, interaction, active_trade):
    requestor = await self.bot.current_guild.fetch_member(active_trade["requestor_id"])
    requestee = await self.bot.current_guild.fetch_member(active_trade["requestee_id"])
    prestige_tier = PRESTIGE_TIERS[active_trade['prestige_level']]

    await interaction.response.edit_message(
      embed=discord.Embed(
        title="Trade Declined",
        description=f"You've declined the proposed {prestige_tier} Trade with **{requestor.display_name}**.\n\nIf their DMs are open, they've been sent a notification to let them know.",
        color=discord.Color.blurple()
      ),
      view=None,
      attachments=[]
    )

    await db_decline_trade(active_trade)

    offered_badge_names, requested_badge_names = await get_offered_and_requested_badge_names(active_trade)

    user = await get_user(requestor.id)
    if user["receive_notifications"]:
      try:
        embed = discord.Embed(
          title="Trade Declined",
          description=f"Your USS Hood {prestige_tier} Badge Trade to **{requestee.display_name}** was declined.",
          color=discord.Color.dark_purple()
        )
        embed.add_field(name=f"Offered by {requestor.display_name}", value=offered_badge_names)
        embed.add_field(name=f"Requested from {requestee.display_name}", value=requested_badge_names)
        embed.set_footer(text="Thank you and have a nice day!")
        await requestor.send(embed=embed)
      except discord.Forbidden:
        logger.info(f"Unable to send trade declined message to {requestor.display_name}, they have their DMs closed.")


  #   _________ __                 __
  #  /   _____//  |______ ________/  |_
  #  \_____  \\   __\__  \\_  __ \   __\
  #  /        \|  |  / __ \|  | \/|  |
  # /_______  /|__| (____  /__|   |__|
  #         \/           \/
  @trade.command(
    name="start",
    description="Start a trade with a specified user (only one outgoing trade active at a time)"
  )
  @option(
    "user",
    discord.User,
    description="The user you wish to start a trade with",
    required=True
  )
  @option(
    name="prestige",
    description="Which Prestige Tier to trade?",
    required=True,
    autocomplete=autocomplete_prestige_tiers
  )
  @option(
    "offer",
    str,
    description="A badge you are offering",
    required=True,
    autocomplete=autocomplete_offering_badges
  )
  @option(
    "request",
    str,
    description="A badge you are requesting",
    required=False,
    autocomplete=autocomplete_requesting_badges
  )
  @commands.check(access_check)
  async def start(self, ctx:discord.ApplicationContext, requestee:discord.User, prestige:str, offer: str, request: str):
    await ctx.defer(ephemeral=True)
    requestor_id = ctx.author.id
    requestee_id = requestee.id

    if not await is_prestige_valid(ctx, prestige):
      return
    prestige = int(prestige)

    # Ensure both users are eligible for this prestige tier
    requestor_echelon_progress = await db_get_echelon_progress(requestor_id)
    requestee_echelon_progress = await db_get_echelon_progress(requestee_id)

    if requestor_echelon_progress['current_prestige_tier'] < prestige:
      await ctx.respond(embed=discord.Embed(
        title="Invalid Trade",
        description=f"You are not eligible to trade {PRESTIGE_TIERS[prestige]} badges.",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    if requestee_echelon_progress['current_prestige_tier'] < prestige:
      await ctx.respond(embed=discord.Embed(
        title="Invalid Trade",
        description=f"{requestee.display_name} is not eligible to trade {PRESTIGE_TIERS[prestige]} badges.",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    if not await self._is_trade_initialization_valid(ctx, requestee):
      return

    if not await self._do_participants_own_badges(ctx, requestor_id, requestee_id, prestige, offer, request):
      return

    trade_id = await db_initiate_trade(requestor_id, requestee_id, prestige)
    active_trade = {
      'id': trade_id,
      'requestor_id': requestor_id,
      'requestee_id': requestee_id,
      'prestige_level': prestige
    }

    try:
      offer_instance_id = int(offer)
    except ValueError:
      await ctx.respond(embed=discord.Embed(
        title="Invalid Badge Selection",
        description="Please select a valid badge from the dropdown.",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    # Checks for special badges/etc
    if await self._is_untradeable(ctx, offer_instance_id, ctx.author, requestee, active_trade, 'offer'):
      return
    await db_add_offered_instance(trade_id, offer_instance_id)

    if request:
      try:
        request_instance_id = int(request)
      except ValueError:
        await ctx.respond(embed=discord.Embed(
          title="Invalid Badge Selection",
          description="Please select a valid badge from the dropdown.",
          color=discord.Color.red()
        ), ephemeral=True)
        return

      if await self._is_untradeable(ctx, request_instance_id, ctx.author, requestee, active_trade, 'request'):
        return
      await db_add_requested_instance(trade_id, request_instance_id)


    initiated_trade = await self.check_for_active_trade(ctx)
    offered_badge_names, requested_badge_names = await get_offered_and_requested_badge_names(initiated_trade)

    # Paginator Pages
    initiated_embed = discord.Embed(
      title="Trade Started!",
      description=f"Your pending {PRESTIGE_TIERS[prestige]} Trade has been started!\n\n"
                  f"If you have additional badges you need to offer and request, use `/trade send` afterwards to finalize or cancel.\n\n"
                  f"Note: You may only have one open outgoing trade request at a time!",
      color=discord.Color.dark_purple()
    ).set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
      icon_url="https://i.imgur.com/GTN4gQG.jpg"
    )

    initiated_embed.add_field(
      name=f"Offered by you",
      value=offered_badge_names
    )
    initiated_embed.add_field(
      name=f"Requested from {requestee.display_name}",
      value=requested_badge_names
    )

    initiated_image = discord.File(fp="./images/trades/assets/trade_pending.png", filename="trade_pending.png")
    initiated_embed.set_image(url=f"attachment://trade_pending.png")

    initiated_pages = [
      pages.Page(embeds=[initiated_embed], files=[initiated_image]),
    ]

    # Offered page
    offered_embed, offered_image = await self._generate_offered_embed_and_image(initiated_trade)
    initiated_pages.append(pages.Page(embeds=[offered_embed], files=[offered_image]))

    # Requested page
    requested_embed, requested_image = await self._generate_requested_embed_and_image(initiated_trade)
    initiated_pages.append(pages.Page(embeds=[requested_embed], files=[requested_image]))

    view = SendCancelView(self, initiated_trade)
    paginator = pages.Paginator(
      pages=initiated_pages,
      use_default_buttons=False,
      custom_buttons=self.trade_buttons,
      custom_view=view,
      loop_pages=True,
      disable_on_timeout=False
    )

    await paginator.respond(ctx.interaction, ephemeral=True)


  async def _is_trade_initialization_valid(self, ctx:discord.ApplicationContext, requestee:discord.User):
    requestor_id = ctx.author.id
    requestee_id = requestee.id

    if requestor_id == requestee_id:
      await ctx.followup.send(embed=discord.Embed(
        title="Don't be silly!",
        description="You can't request a trade from yourself!",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    if requestee_id == self.bot.user.id:
      await ctx.followup.send(embed=discord.Embed(
        title="Nope",
        description="AGIMUS has no badges to trade!",
        color=discord.Color.red()
      ), ephemeral=True)
      return False

    # Deny requests to users that do not have XP enabled
    requestee_details = await get_user(requestee_id)
    if not requestee_details or not requestee_details["xp_enabled"]:
      opted_out_embed = discord.Embed(
        title="This user is not participating.",
        description=f"Sorry, **{requestee.display_name}** has opted out of the XP system and is not available for trading.",
        color=discord.Color.red()
      )
      await ctx.followup.send(embed=opted_out_embed, ephemeral=True)
      return False

    # Deny the trade request if there's an existing trade in progress by the requestor
    active_trade = await db_get_active_requestor_trade(requestor_id)
    if active_trade:
      active_trade_requestee = await self.bot.current_guild.fetch_member(active_trade['requestee_id'])
      already_active_embed = discord.Embed(
        title="You already have an active trade!",
        description=f"You have a outgoing trade open with **{active_trade_requestee.display_name}**.\n\nUse `/trade send` "
                    f"to check the status and cancel the current trade if desired!\n\nThis must be resolved before "
                    f"you can open another request.",
        color=discord.Color.red()
      )
      already_active_embed.set_footer(text="You may want to check on this trade to see if they have had a chance to "
                                            "review your request!")
      await ctx.followup.send(embed=already_active_embed, ephemeral=True)
      return False

    # Deny the trade request if the requestee already has too many active trades pending
    requestee_trades = await db_get_active_requestee_trades(requestee_id)
    if len(requestee_trades) >= self.max_trades:
      max_requestee_trades_embed = discord.Embed(
        title=f"{requestee.display_name} has too many pending trades!",
        description=f"Sorry, the person you've requested a trade from already has the maximum number of incoming "
                    f"trade requests pending ({self.max_trades}).",
        color=discord.Color.red()
      )
      await ctx.followup.send(embed=max_requestee_trades_embed, ephemeral=True)
      return False

    # No validation problems
    return True


  async def _do_participants_own_badges(self, ctx, requestor_id, requestee_id, prestige_level, offer_instance_id, request_instance_id=None):
    offer_instance = await db_get_badge_instance_by_id(int(offer_instance_id))
    if not offer_instance or offer_instance['owner_discord_id'] != str(requestor_id) or offer_instance['prestige_level'] != prestige_level:
      await ctx.respond(embed=discord.Embed(
        title="Invalid Offer",
        description="You don't own that badge at the specified Prestige Tier.",
        color=discord.Color.red()
      ), ephemeral=True)
      return False

    if request_instance_id:
      request_instance = await db_get_badge_instance_by_id(int(request_instance_id))
      if not request_instance or request_instance['owner_discord_id'] != str(requestee_id) or request_instance['prestige_level'] != prestige_level:
        requestee = await self.bot.current_guild.fetch_member(requestee_id)
        await ctx.respond(embed=discord.Embed(
          title="Invalid Request",
          description=f"{requestee.display_name} does not own that badge at the specified Prestige Tier.",
          color=discord.Color.red()
        ), ephemeral=True)
        return False

    return True

  #   _________                  .___
  #  /   _____/ ____   ____    __| _/
  #  \_____  \_/ __ \ /    \  / __ |
  #  /        \  ___/|   |  \/ /_/ |
  # /_______  /\___  >___|  /\____ |
  #         \/     \/     \/      \/
  @trade.command(
    name="send",
    description="Check the current status and send your outgoing trade"
  )
  @commands.check(access_check)
  async def send(self, ctx):
    active_trade = await self.check_for_active_trade(ctx)
    if not active_trade:
      return

    logger.info(f"{Fore.CYAN}{ctx.author.display_name} is checking the status of their current trade.{Style.RESET_ALL}")
    await ctx.defer(ephemeral=True)

    trade_pages = await self._generate_trade_pages(active_trade)
    view = SendCancelView(self, active_trade)
    paginator = pages.Paginator(
      pages=trade_pages,
      use_default_buttons=False,
      custom_buttons=self.trade_buttons,
      custom_view=view,
      loop_pages=True,
      disable_on_timeout=False
    )

    await paginator.respond(ctx.interaction, ephemeral=True)

  async def _cancel_trade_callback(self, interaction, active_trade):
    try:
      await db_cancel_trade(active_trade)
      requestor = await self.bot.current_guild.fetch_member(active_trade["requestor_id"])
      requestee = await self.bot.current_guild.fetch_member(active_trade["requestee_id"])
      prestige_tier = PRESTIGE_TIERS[active_trade['prestige_level']]

      embed = discord.Embed(
        title=f"{prestige_tier} Trade Canceled!",
        description=f"Your {prestige_tier} Trade with **{requestee.display_name}** has been canceled!\n\nYou may now begin a new trade request with `/trade start`.",
        color=discord.Color.dark_red()
      )

      if active_trade["status"] == 'active':
        embed.set_footer(text="Because the trade was active, we've let them know you have canceled the request.")

        # Notify requestee if they have notifications enabled
        user_settings = await get_user(requestee.id)
        if user_settings["receive_notifications"]:
          try:
            offered_badge_names, requested_badge_names = await get_offered_and_requested_badge_names(active_trade)

            notification = discord.Embed(
              title=f"{prestige_tier} Trade Canceled!",
              description=f"Heads up! **{requestor.display_name}** has canceled their pending {prestige_tier} Trade request with you.",
              color=discord.Color.dark_purple()
            )
            notification.add_field(
              name=f"{prestige_tier} Badges offered by {requestor.display_name}",
              value=offered_badge_names
            )
            notification.add_field(
              name=f"{prestige_tier} Badges requested from {requestee.display_name}",
              value=requested_badge_names
            )
            notification.set_footer(text="Note: You can use /settings to enable or disable these messages.")

            await requestee.send(embed=notification)
          except discord.Forbidden:
            logger.info(f"Unable to send cancelation message to {requestee.display_name}, DMs closed.")

      await interaction.response.edit_message(
        embed=embed,
        view=None,
        attachments=[]
      )

    except Exception:
      logger.info(traceback.format_exc())


  async def _send_trade_callback(self, interaction, active_trade):
    try:
      # Activate the trade and send confirmation
      await db_activate_trade(active_trade)
      requestor = await self.bot.current_guild.fetch_member(active_trade["requestor_id"])
      requestee = await self.bot.current_guild.fetch_member(active_trade["requestee_id"])
      prestige_tier = PRESTIGE_TIERS[active_trade['prestige_level']]

      logger.info(f"{Fore.CYAN}{requestor.display_name} has activated a {prestige_tier} Trade with {requestee.display_name}{Style.RESET_ALL}")

      await interaction.response.edit_message(
        embed=discord.Embed(
          title=f"{prestige_tier} Trade Sent!",
          color=discord.Color.dark_purple()
        ),
        view=None,
        attachments=[]
      )

      # Stash active as status for generating embeds/images
      active_trade["status"] = "active"
      # Home Page
      home_embed, home_image = await self._generate_home_embed_and_image(active_trade)
      # Offered page
      offered_embed, offered_image = await self._generate_offered_embed_and_image(active_trade)
      # Requested Page
      requested_embed, requested_image = await self._generate_requested_embed_and_image(active_trade)

      home_message = await interaction.channel.send(embed=home_embed, file=home_image)
      await interaction.channel.send(embed=offered_embed, file=offered_image)
      await interaction.channel.send(embed=requested_embed, file=requested_image)

      # Give notice to Requestee
      user = await get_user(requestee.id)
      if user["receive_notifications"]:
        try:
          offered_badge_names, requested_badge_names = await get_offered_and_requested_badge_names(active_trade)

          title = "Trade Offered"
          description = f"Hey there, wanted to let you know that **{requestor.display_name}** has requested a {prestige_tier} Trade from you on The USS Hood.\n\n"
          description += f"Use `/trade incoming` in the channel to review and either accept or deny!\n\nYou can jump to their offer directly at at {home_message.jump_url}!"

          requestee_embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.dark_purple()
          )
          requestee_embed.add_field(
            name=f"{prestige_tier} Badges offered by {requestor.display_name}",
            value=offered_badge_names
          )
          requestee_embed.add_field(
            name=f"{prestige_tier} Badges requested from {requestee.display_name}",
            value=requested_badge_names
          )
          requestee_embed.set_footer(
            text="Note: You can use /settings to enable or disable these messages."
          )
          await requestee.send(embed=requestee_embed)
        except discord.Forbidden as e:
          logger.info(f"Unable to send trade cancelation message to {requestor.display_name}, they have their DMs closed.")
          pass
    except Exception as e:
      logger.info(traceback.format_exc())


  async def _generate_trade_pages(self, active_trade):
    # Home Page
    home_embed, home_image = await self._generate_home_embed_and_image(active_trade)
    # Offered page
    offered_embed, offered_image = await self._generate_offered_embed_and_image(active_trade)
    # Requested Page
    requested_embed, requested_image = await self._generate_requested_embed_and_image(active_trade)

    # Paginator Pages
    trade_pages = [
      pages.Page(
        embeds=[home_embed],
        files=[home_image]
      ),
      pages.Page(
        embeds=[offered_embed],
        files=[offered_image]
      ),
      pages.Page(
        embeds=[requested_embed],
        files=[requested_image]
      )
    ]

    return trade_pages

  async def _generate_offered_embed_and_image(self, active_trade):
    requestee = await self.bot.current_guild.fetch_member(active_trade["requestee_id"])
    requestor = await self.bot.current_guild.fetch_member(active_trade["requestor_id"])
    prestige_tier = PRESTIGE_TIERS[active_trade['prestige_level']]

    offered_instances = await db_get_trade_offered_badge_instances(active_trade)  # full enriched

    offered_image, offered_filename = await generate_badge_trade_images(
      offered_instances,
      f"{prestige_tier} Badges offered by {requestor.display_name}",
      f"{len(offered_instances)} Badges"
    )

    offered_embed = discord.Embed(
      title="Offered",
      description=f"{prestige_tier} Badges offered by **{requestor.display_name}** to **{requestee.display_name}**",
      color=discord.Color.dark_purple()
    )
    offered_embed.set_image(url=offered_filename)

    return offered_embed, offered_image


  async def _generate_requested_embed_and_image(self, active_trade):
    requestee = await self.bot.current_guild.fetch_member(active_trade["requestee_id"])
    requestor = await self.bot.current_guild.fetch_member(active_trade["requestor_id"])
    prestige_tier = PRESTIGE_TIERS[active_trade['prestige_level']]

    requested_instances = await db_get_trade_requested_badge_instances(active_trade)

    requested_image, requested_filename = await generate_badge_trade_images(
      requested_instances,
      f"{prestige_tier} Badges requested from {requestee.display_name}",
      f"{len(requested_instances)} Badges"
    )

    requested_embed = discord.Embed(
      title="Requested",
      description=f"{prestige_tier} Badges requested from **{requestee.display_name}** by **{requestor.display_name}**",
      color=discord.Color.dark_purple()
    )
    requested_embed.set_image(url=requested_filename)

    return requested_embed, requested_image

  async def _generate_home_embed_and_image(self, active_trade):
    requestor = await self.bot.current_guild.fetch_member(active_trade["requestor_id"])
    requestee = await self.bot.current_guild.fetch_member(active_trade["requestee_id"])
    prestige_tier = PRESTIGE_TIERS[active_trade['prestige_level']]

    offered_badge_names, requested_badge_names = await get_offered_and_requested_badge_names(active_trade)

    if active_trade["status"] == 'active':
      title = "Trade Offered!"
      description = (
        f"Get that, get that, gold pressed latinum!\n\n"
        f"**{requestor.display_name}** has offered a {prestige_tier} Trade to **{requestee.display_name}**!"
      )
      image_filename = "trade_offer.png"
      color = discord.Color.dark_purple()

    elif active_trade["status"] == 'pending':
      title = "Trade Pending..."
      description = (
        f"Ready to send?\n\nThis is your pending {prestige_tier} Trade with **{requestee.display_name}**.\n\n"
        "Press the **Send** button below if it looks good to go!"
      )
      image_filename = "trade_pending.png"
      color = discord.Color(0x99aab5)

    home_embed = discord.Embed(
      title=title,
      description=description,
      color=color
    )
    home_embed.add_field(
      name=f"{prestige_tier} Badges offered by {requestor.display_name}",
      value=offered_badge_names
    )
    home_embed.add_field(
      name=f"{prestige_tier} Badges requested from {requestee.display_name}",
      value=requested_badge_names
    )
    home_embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
      icon_url="https://i.imgur.com/GTN4gQG.jpg"
    )
    home_image = discord.File(fp=f"./images/trades/assets/{image_filename}", filename=image_filename)
    home_embed.set_image(url=f"attachment://{image_filename}")

    return home_embed, home_image


  # __________
  # \______   \_______  ____ ______   ____  ______ ____
  #  |     ___/\_  __ \/  _ \\____ \ /  _ \/  ___// __ \
  #  |    |     |  | \(  <_> )  |_> >  <_> )___ \\  ___/
  #  |____|     |__|   \____/|   __/ \____/____  >\___  >
  #                          |__|              \/     \/
  @trade.command(
    name="propose",
    description="Offer or Request badges for your current pending trade"
  )
  @option(
    'offer',
    str,
    description="A badge you are offering",
    required=False,
    autocomplete=autocomplete_offering_badges,
  )
  @option(
    'request',
    str,
    description="A badge you are requesting",
    required=False,
    autocomplete=autocomplete_requesting_badges,
  )
  @commands.check(access_check)
  async def propose(self, ctx, offer:str, request:str):
    active_trade = await self.check_for_active_trade(ctx)
    if not active_trade:
      return

    requestor_echelon_progress = await db_get_echelon_progress(active_trade["requestor_id"])
    requestee_echelon_progress = await db_get_echelon_progress(active_trade["requestee_id"])

    if requestor_echelon_progress['current_prestige_tier'] < active_trade['prestige_level'] or requestee_echelon_progress['current_prestige_tier'] < active_trade['prestige_level']:
      await db_cancel_trade(active_trade)
      await ctx.respond(embed=discord.Embed(
        title="Trade Invalid",
        description=f"One or both participants are not eligible for {PRESTIGE_TIERS[active_trade['prestige_level']]} badge trading.",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    if not offer and not request:
      await ctx.respond(embed=discord.Embed(
        title="Please select a badge to offer or trade",
        description="If you want to update your trade, you need to give a badge.",
        color=discord.Color.dark_red()
      ), ephemeral=True)
      return

    if offer:
      try:
        offer_id = int(offer)
      except ValueError:
        await ctx.respond(embed=discord.Embed(
          title="Invalid Badge Selection",
          description="Please select a valid badge from the dropdown.",
          color=discord.Color.red()
        ), ephemeral=True)
        return
      if await self._is_untradeable(ctx, offer_id, ctx.author, await self.bot.fetch_user(active_trade['requestee_id']), active_trade, 'offer'):
        return
      await self._add_offered_badge_to_trade(ctx, active_trade, offer_id)

    if request:
      try:
        request_id = int(request)
      except ValueError:
        await ctx.respond(embed=discord.Embed(
          title="Invalid Badge Selection",
          description="Please select a valid badge from the dropdown.",
          color=discord.Color.red()
        ), ephemeral=True)
        return
      if await self._is_untradeable(ctx, request_id, ctx.author, await self.bot.fetch_user(active_trade['requestee_id']), active_trade, 'request'):
        return
      await self._add_requested_badge_to_trade(ctx, active_trade, request_id)


  async def _add_offered_badge_to_trade(self, ctx, active_trade, instance_id):
    trade_id = active_trade["id"]
    requestee = await self.bot.current_guild.fetch_member(active_trade["requestee_id"])
    requestor = await self.bot.current_guild.fetch_member(active_trade["requestor_id"])
    prestige_tier = PRESTIGE_TIERS[active_trade['prestige_level']]

    user_instances = await db_get_user_badge_instances(requestor.id, prestige=active_trade['prestige_level'])
    instance = next((b for b in user_instances if b["badge_instance_id"] == instance_id), None)
    if not instance:
      await ctx.respond(embed=discord.Embed(
        title="Badge Not Found",
        description=f"You don't own this {prestige_tier} Badge!",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    await db_add_offered_instance(trade_id, instance_id)

    badge_name = instance['badge_name']
    discord_file, attachment_url = await generate_badge_preview(ctx.author.id, instance, disable_overlays=True)

    embed = discord.Embed(
      title=f"Badge added to offer.",
      description=f"**{badge_name}** has been added to your offer to **{requestee.display_name}**",
      color=discord.Color.dark_gold()
    )
    embed.set_image(url=attachment_url)
    if ctx.response.is_done():
      await ctx.followup.send(embed=embed, file=discord_file, ephemeral=True)
    else:
      await ctx.respond(embed=embed, file=discord_file, ephemeral=True)

  async def _add_requested_badge_to_trade(self, ctx, active_trade, instance_id):
    trade_id = active_trade["id"]
    requestee = await self.bot.current_guild.fetch_member(active_trade["requestee_id"])
    prestige_tier = PRESTIGE_TIERS[active_trade['prestige_level']]

    user_instances = await db_get_user_badge_instances(requestee.id, prestige=active_trade['prestige_level'])
    instance = next((b for b in user_instances if b["badge_instance_id"] == instance_id), None)
    if not instance:
      await ctx.respond(embed=discord.Embed(
        title="Badge Not Found",
        description=f"**{requestee.display_name}** doesn't own that {prestige_tier} Badge!",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    await db_add_requested_instance(trade_id, instance_id)

    badge_name = instance['badge_name']
    discord_file, attachment_url = await generate_badge_preview(ctx.author.id, instance, disable_overlays=True)

    embed = discord.Embed(
      title=f"Badge added to request.",
      description=f"**{badge_name}** has been added to your request from **{requestee.display_name}**",
      color=discord.Color.dark_gold()
    )
    embed.set_image(url=attachment_url)
    if ctx.response.is_done():
      await ctx.followup.send(embed=embed, file=discord_file, ephemeral=True)
    else:
      await ctx.respond(embed=embed, file=discord_file, ephemeral=True)


  async def _is_untradeable(self, ctx, badge_instance_id, requestor, requestee, active_trade, direction):
    if direction == 'offer':
      dir_preposition = 'to'
      from_user = requestor
      to_user = requestee
      side_fetcher = db_get_trade_offered_badge_instances
    else:
      dir_preposition = 'from'
      from_user = requestee
      to_user = requestor
      side_fetcher = db_get_trade_requested_badge_instances

    instance = await db_get_badge_instance_by_id(badge_instance_id)
    if not instance:
      await ctx.respond(embed=discord.Embed(
        title="Badge not found",
        description="This badge no longer exists or was already traded.",
        color=discord.Color.red()
      ), ephemeral=True)
      return True

    # They shouldn't able to select badges from other prestige levels but just in case.. ?
    if instance['prestige_level'] != active_trade['prestige_level']:
      await ctx.respond(
        embed=discord.Embed(
          title="Invalid Prestige!",
          description=f"WTF? You've selected a badge at the incorrect Prestige Level... (Somehow?)",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return True

    # Must be owned by from_user
    if str(instance['owner_discord_id']) != str(from_user.id):
      await ctx.respond(embed=discord.Embed(
        title="Badge not available",
        description=f"{from_user.display_name} no longer has this badge. It may have already been traded or removed.",
        color=discord.Color.red()
      ), ephemeral=True)
      return True

    # Special check
    if instance['special']:
      await ctx.respond(embed=discord.Embed(
        title="That badge is untradeable!",
        description=f"Sorry, you can't {direction} **{instance['badge_name']}** — it's a very shiny and special one!",
        color=discord.Color.red()
      ), ephemeral=True)
      return True

    # The receiving user already owns this badge type
    to_user_instances = await db_get_user_badge_instances(to_user.id, prestige=active_trade['prestige_level'])
    to_user_badge_filenames = {b['badge_filename'] for b in to_user_instances}
    if instance['badge_filename'] in to_user_badge_filenames:
      await ctx.respond(embed=discord.Embed(
        title=f"{to_user.display_name} already has {instance['badge_name']} at the specified Prestige Tier!",
        description=f"No need to {direction} this one!",
        color=discord.Color.red()
      ), ephemeral=True)
      return True

    # Already part of this trade
    trade_badges = await side_fetcher(active_trade)
    trade_badge_ids = {b['badge_instance_id'] for b in trade_badges}
    if instance['badge_instance_id'] in trade_badge_ids:
      await ctx.respond(embed=discord.Embed(
        title=f"{instance['badge_name']} already exists in {direction} list.",
        description="No action taken.",
        color=discord.Color.red()
      ), ephemeral=True)
      return True

    # Max per-side badge count
    if len(trade_badges) >= self.max_badges_per_trade:
      await ctx.respond(embed=discord.Embed(
        title=f"Unable to add {instance['badge_name']} to {direction} list.",
        description=f"You're at the max number of badges allowed per trade ({self.max_badges_per_trade})!",
        color=discord.Color.red()
      ), ephemeral=True)
      return True

    # Max badge cap protection
    max_badge_count = await db_get_max_badge_count()
    to_user_count = await db_get_badge_instances_count_for_user(to_user.id, prestige=active_trade['prestige_level'])
    if direction == 'offer':
      incoming = await db_get_trade_offered_badge_instances(active_trade)
    else:
      incoming = await db_get_trade_requested_badge_instances(active_trade)

    if to_user_count + len(incoming) + 1 > max_badge_count:
      await ctx.respond(embed=discord.Embed(
        title=f"{to_user.display_name}'s inventory is full!",
        description=f"Adding **{instance['badge_name']}** would exceed the total number of badges possible at this the specified Prestige Tier ({max_badge_count}).",
        color=discord.Color.red()
      ), ephemeral=True)
      return True

    return False


  async def check_for_active_trade(self, ctx: discord.ApplicationContext):
    """
    Return the active trade started by this user.  If it doesn't exist, show an error message.
    """
    active_trade = await db_get_active_requestor_trade(ctx.author.id)

    # If we don't have an active trade for this user, go ahead and let them know
    if not active_trade:
      inactive_embed = discord.Embed(
        title="You don't have a pending or active trade open!",
        description="You can start a new trade with `/trade start`!",
        color=discord.Color.red()
      )
      await ctx.respond(embed=inactive_embed, ephemeral=True)

    return active_trade
