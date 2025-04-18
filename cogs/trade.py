from common import *
from queries.wishlist import db_autolock_badges_by_filenames_if_in_wishlist, db_get_user_wishlist_badges
from utils.badge_utils import *
from utils.check_channel_access import access_check
from utils.check_user_access import user_check

from random import sample

f = open("./data/rules_of_acquisition.txt", "r")
data = f.read()
rules_of_acquisition = data.split("\n")
f.close()

#    _____          __                                     .__          __
#   /  _  \  __ ___/  |_  ____   ____  ____   _____ ______ |  |   _____/  |_  ____
#  /  /_\  \|  |  \   __\/  _ \_/ ___\/  _ \ /     \\____ \|  | _/ __ \   __\/ __ \
# /    |    \  |  /|  | (  <_> )  \__(  <_> )  Y Y  \  |_> >  |_\  ___/|  | \  ___/
# \____|__  /____/ |__|  \____/ \___  >____/|__|_|  /   __/|____/\___  >__|  \___  >
#         \/                        \/            \/|__|             \/          \/
async def autocomplete_offering_badges(ctx: discord.AutocompleteContext):
  """
  Autocomplete of badges that the user making the trade has and are not already in the other user’s collection.
  """
  # Find the user in the other end of the trade, either from the user selection or the existing trade
  requestee_id = None
  if 'requestee' in ctx.options:
    requestee_id = ctx.options['requestee']
  else:
    active_trade = await db_get_active_requestor_trade(ctx.interaction.user.id)
    if active_trade:
      requestee_id = active_trade['requestee_id']

  requestor_badges = [b['badge_name'] for b in await db_get_user_badges(ctx.interaction.user.id)]
  if requestee_id:
    requestee_badges = [b['badge_name'] for b in await db_get_user_badges(requestee_id)]
    badge_names = [b for b in requestor_badges if b not in requestee_badges]
  else:
    badge_names = requestor_badges

  special_badges = await db_get_special_badges()
  special_badge_names = [b['badge_name'] for b in special_badges]
  badge_names = [b for b in badge_names if b not in special_badge_names]

  if len(badge_names) == 0:
    badge_names = ["This user already has all badges that you possess! Use '/trade cancel' to cancel this trade."]

  badge_names.sort()
  return [result for result in badge_names if ctx.value.lower() in result.lower()]


async def autocomplete_requesting_badges(ctx: discord.AutocompleteContext):
  """
  Autocomplete of badges that the user on the other end of the trade has, and this user doesn’t
  """
  # Find the user in the other end of the trade, either from the user selection or the existing trade
  requestee_id = None
  if 'requestee' in ctx.options:
    requestee_id = ctx.options['requestee']
  else:
    active_trade = await db_get_active_requestor_trade(ctx.interaction.user.id)
    if active_trade:
      requestee_id = active_trade['requestee_id']

  if requestee_id:
    requestor_badges = [b['badge_name'] for b in await db_get_user_badges(ctx.interaction.user.id)]
    requestee_badges = [b['badge_name'] for b in await db_get_user_badges(requestee_id)]
    badge_names = [b for b in requestee_badges if b not in requestor_badges]
  else:
    badge_names = ["Use '/trade start' to start a trade and make sure you choose someone."]

  special_badge_names = [b['badge_name'] for b in await db_get_special_badges()]
  badge_names = [b for b in badge_names if b not in special_badge_names]

  if len(badge_names) == 0:
    badge_names = ["You already have all badges that this user possesses! Use '/trade cancel' to cancel this trade."]

  badge_names.sort()
  return [result for result in badge_names if ctx.value.lower() in result.lower()]


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
  def __init__(self, cog, active_trade, trade_contains_badges):
    super().__init__()

    self.add_item(CancelButton(cog, active_trade))
    if active_trade["status"] != 'active' and trade_contains_badges:
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
      pages.PaginatorButton("prev", label="    ⬅     ", style=discord.ButtonStyle.primary, row=1),
      pages.PaginatorButton(
        "page_indicator", style=discord.ButtonStyle.gray, disabled=True, row=1
      ),
      pages.PaginatorButton("next", label="     ➡    ", style=discord.ButtonStyle.primary, row=1),
    ]

  trade = discord.SlashCommandGroup("trade", "Commands for trading badges")


  #   ___                   _             _____            _
  #  |_ _|_ _  __ ___ _ __ (_)_ _  __ _  |_   _| _ __ _ __| |___
  #   | || ' \/ _/ _ \ '  \| | ' \/ _` |   | || '_/ _` / _` / -_)
  #  |___|_||_\__\___/_|_|_|_|_||_\__, |   |_||_| \__,_\__,_\___|
  #                               |___/
  @trade.command(
    name="incoming",
    description="View and accept/decline incoming trades from other users"
  )
  @commands.check(access_check)
  @commands.check(user_check)
  async def incoming(self, ctx:discord.ApplicationContext):
    incoming_trades = await db_get_active_requestee_trades(ctx.user.id)

    if not incoming_trades:
      await ctx.respond(embed=discord.Embed(
          title="No Incoming Trade Requests",
          description="No one has any active trades requested from you. Get out there, arrr, start hustlin' me heartie!",
          color=discord.Color.blurple()
        ),
        ephemeral=True
      )
      return

    if type(incoming_trades) is not list:
      incoming_trades = [incoming_trades]

    incoming_requestor_ids = [int(t["requestor_id"]) for t in incoming_trades]
    requestors = []
    for user_id in incoming_requestor_ids:
      requestor = await self.bot.current_guild.fetch_member(user_id)
      requestors.append(requestor)

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

  async def _send_pending_trade_interface(self, interaction, requestor_id):
    requestee_id = interaction.user.id
    active_trade = await db_get_active_trade_between_requestor_and_requestee(requestor_id, requestee_id)

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
    offered_badge_names, requested_badge_names = await get_offered_and_requested_badge_names(active_trade)

    # FAILSAFES!

    # Check offered badges and check requested badges
    # Ensure users do not ALREADY have them currently
    # If they do, then cancel the trade
    requestor_already_has_badges = await self._requestor_already_has_badges(interaction, active_trade, requestor, requestee)
    if requestor_already_has_badges:
      return

    requestee_already_has_badges = await self._requestee_already_has_badges(interaction, active_trade, requestor, requestee)
    if requestee_already_has_badges:
      return

    # Check offered badges and check requested badges
    # Ensure users STILL have them available to trade
    # If they don't, then cancel the trade
    requestor_still_has_badges = await self._requestor_still_has_badges(interaction, active_trade, requestor, requestee)
    if not requestor_still_has_badges:
      return

    requestee_still_has_badges = await self._requestee_still_has_badges(interaction, active_trade, requestor, requestee)
    if not requestee_still_has_badges:
      return

    # If failsafes pass, go ahead with the transfer!

    # Perform the actual swap
    await db_perform_badge_transfer(active_trade)
    await db_complete_trade(active_trade)

    # Lock badges the users now possess that were in their wishlists
    # Stash the wishlist badges prior to purging to alert users in Dabo matches if they've acquired a Wishlist item
    requestors_previous_wishlist_badges = await db_get_user_wishlist_badges(requestor.id)
    requested_badges = await db_get_trade_requested_badges(active_trade)
    await db_autolock_badges_by_filenames_if_in_wishlist(requestor.id, [b['badge_filename'] for b in requested_badges])

    requestees_previous_wishlist_badges = await db_get_user_wishlist_badges(requestee.id)
    offered_badges = await db_get_trade_offered_badges(active_trade)
    await db_autolock_badges_by_filenames_if_in_wishlist(requestee.id, [b['badge_filename'] for b in offered_badges])

    # Delete Badges From Users Wishlists
    await db_purge_users_wishlist(requestor.id)
    await db_purge_users_wishlist(requestee.id)

    # Set up text differences between Dabo and Regular Confirmation Embeds
    footer_text = f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}"

    if active_trade["type"] == 'dabo':
      title = "DABO COMPLETE!"
      description = f"**{requestor.display_name}** 🔄 **{requestee.display_name}**!\n\nRandomized badges transferred successfully!\n## DABO!!!"
      image_filename = "dabo_successful.jpg"

      # Indicate Wishlist Dabo wins via ✨s in summary fields if Dabo-ness Achieved
      # (99% of non-Dabo trades are wishlist related we don't really need to indicate this normally)
      requested_wishlist_badges_received = [b for b in requested_badges if b['badge_filename'] in [w['badge_filename'] for w in requestors_previous_wishlist_badges]]
      requested_badge_names = "\n".join([f"* {b['badge_name']}{' ✨' if b['badge_filename'] in [w['badge_filename'] for w in requested_wishlist_badges_received] else ''}" for b in requested_badges])

      offered_wishlist_badges_received = [b for b in offered_badges if b['badge_filename'] in [w['badge_filename'] for w in requestees_previous_wishlist_badges]]
      offered_badge_names = "\n".join([f"* {b['badge_name']}{' ✨' if b['badge_filename'] in [w['badge_filename'] for w in offered_wishlist_badges_received] else ''}" for b in offered_badges])

      if len(requested_wishlist_badges_received) or len(offered_wishlist_badges_received):
        footer_text += "\n\n✨ - Indicates a DABO WISHLIST WIN!"
    else:
      title = "Successful Trade!"
      description = f"**{requestor.display_name}** and **{requestee.display_name}** came to an agreement!\n\nBadges transferred successfully!"
      image_filename = "trade_successful.jpg"

    # Send Message to Channel
    success_embed = discord.Embed(
      title=title,
      description=description,
      color=discord.Color.dark_purple()
    )
    success_embed.add_field(
      name=f"{requestor.display_name} received",
      value=requested_badge_names
    )
    success_embed.add_field(
      name=f"{requestee.display_name} received",
      value=offered_badge_names
    )
    success_image = discord.File(fp=f"./images/trades/assets/{image_filename}", filename=image_filename)
    success_embed.set_image(url=f"attachment://{image_filename}")
    success_embed.set_footer(
      text=footer_text,
      icon_url="https://i.imgur.com/GTN4gQG.jpg"
    )

    channel = interaction.channel
    message = await channel.send(embed=success_embed, file=success_image)

    # Send notification to requestor that the trade was successful
    requestor_user = await get_user(requestor.id)
    if requestor_user["receive_notifications"]:
      try:
        success_embed.add_field(
          name="View Confirmation",
          value=f"{message.jump_url}",
          inline=False
        )
        success_embed.set_footer(
          text="Note: You can use /settings to enable or disable these messages."
        )
        await requestor.send(embed=success_embed)
      except discord.Forbidden as e:
        logger.info(f"Unable to send trade confirmation message to {requestor.display_name}, they have their DMs closed.")
        pass

       # Send notification to requestor if they completed a Dabo Trade and got some Wishlist badges
      if active_trade["type"] == 'dabo':
        requestor_wishlisted_badge_names = [b['badge_name'] for b in requestors_previous_wishlist_badges]
        requestor_acquired_badge_names = [b['badge_name'] for b in requested_badges]
        requestor_wishlist_successes = [b for b in requestor_acquired_badge_names if b in requestor_wishlisted_badge_names]
        if len(requestor_wishlist_successes):
          try:
            wishlist_success_embed = discord.Embed(
              title="You got some Wishlisted Badges from that Dabo Trade!",
              description=f"Hey just a heads up, one or more of the badges you received from your recent Dabo Trade with **{requestee.display_name}** were on your wishlist! Noice.",
              color=discord.Color.dark_purple()
            )
            wishlist_success_embed.add_field(
              name="Wishlisted Acquisitions",
              value="\n".join([f"* {b}" for b in requestor_wishlist_successes]),
              inline=False
            )
            wishlist_success_embed.set_footer(
              text="Note: You can use /settings to enable or disable these messages."
            )
            await requestor.send(embed=wishlist_success_embed)
          except discord.Forbidden as e:
            logger.info(f"Unable to send Wishlist Acquisition message to {requestor.display_name}, they have their DMs closed.")
            pass

    # Send notification to requestee if they completed a Dabo Trade and got some Wishlist badges
    requestee_user = await get_user(requestee.id)
    if requestee_user["receive_notifications"] and active_trade["type"] == 'dabo':
      requestee_wishlisted_badge_names = [b['badge_name'] for b in requestees_previous_wishlist_badges]
      requestee_acquired_badge_names = [b['badge_name'] for b in offered_badges]
      requestee_wishlist_successes = [b for b in requestee_acquired_badge_names if b in requestee_wishlisted_badge_names]
      if len(requestee_wishlist_successes):
        try:
          wishlist_success_embed = discord.Embed(
            title="You got Wishlisted Badges from that Dabo Trade!",
            description=f"Hey just a heads up, one or more of the badges you received from your recent Dabo Trade with **{requestor.display_name}** were on your wishlist! Noice.",
            color=discord.Color.dark_purple()
          )
          wishlist_success_embed.add_field(
            name="Wishlisted Acquisitions",
            value="\n".join([f"* {b}" for b in requestee_wishlist_successes]),
            inline=False
          )
          wishlist_success_embed.set_footer(
            text="Note: You can use /settings to enable or disable these messages."
          )
          await requestee.send(embed=wishlist_success_embed)
        except discord.Forbidden as e:
          logger.info(f"Unable to send Wishlist Acquisition message to {requestee.display_name}, they have their DMs closed.")
          pass


  async def _cancel_invalid_related_trades(self, active_trade):
    # These are all the active or pending trades that involved either the requestee or
    # requestor and include the badges that are involved with the confirmed trade which
    # are thus no longer valid and need to be canceled
    related_trades = await db_get_related_badge_trades(active_trade)

    # Filter out the current trade itself, then cancel the others
    trades_to_cancel = [t for t in related_trades if t["id"] != active_trade["id"]]
    # Iterate through to cancel, and then
    for trade in trades_to_cancel:
      await db_cancel_trade(trade)
      requestee = await self.bot.current_guild.fetch_member(trade['requestee_id'])
      requestor = await self.bot.current_guild.fetch_member(trade['requestor_id'])

      offered_badge_names, requested_badge_names = await get_offered_and_requested_badge_names(trade)

      # Give notice to Requestee
      user = await get_user(requestee.id)
      if user["receive_notifications"] and trade['status'] == 'active':
        try:
          requestee_embed = discord.Embed(
            title="Trade Canceled",
            description=f"Just a heads up! Your USS Hood Badge Trade initiated by **{requestor.display_name}** was canceled because one or more of the badges involved were traded to another user.",
            color=discord.Color.purple()
          )
          requestee_embed.add_field(
            name=f"Offered by {requestor.display_name}",
            value=offered_badge_names
          )
          requestee_embed.add_field(
            name=f"Requested from {requestee.display_name}",
            value=requested_badge_names
          )
          requestee_embed.set_footer(
            text="Note: You can use /settings to enable or disable these messages."
          )
          await requestee.send(embed=requestee_embed)
        except discord.Forbidden as e:
          logger.info(f"Unable to send trade cancelation message to {requestee.display_name}, they have their DMs closed.")
          pass

      # Give notice to Requestor
      user = await get_user(requestor.id)
      if user["receive_notifications"]:
        try:
          requestor_embed = discord.Embed(
            title="Trade Canceled",
            description=f"Just a heads up! Your USS Hood Badge Trade requested from **{requestee.display_name}** was canceled because one or more of the badges involved were traded to another user.",
            color=discord.Color.purple()
          )
          requestor_embed.add_field(
            name=f"Offered by {requestor.display_name}",
            value=offered_badge_names
          )
          requestor_embed.add_field(
            name=f"Requested from {requestee.display_name}",
            value=requested_badge_names
          )
          requestor_embed.set_footer(
            text="Note: You can use /settings to enable or disable these messages."
          )
          await requestor.send(embed=requestor_embed)
        except discord.Forbidden as e:
          logger.info(f"Unable to send trade cancelation message to {requestor.display_name}, they have their DMs closed.")
          pass


  async def _requestor_already_has_badges(self, interaction, active_trade, requestor, requestee):
    requestor_badges = [b['badge_name'] for b in await db_get_user_badges(active_trade["requestor_id"])]

    trade_requested_badges = await db_get_trade_requested_badges(active_trade)
    trade_requested_badges = [b["badge_name"] for b in trade_requested_badges]

    badges_in_trade_requestor_has = [t for t in requestor_badges if t in trade_requested_badges]

    if len(badges_in_trade_requestor_has) != 0:
      await db_cancel_trade(active_trade)
      await interaction.followup.send(
        embed=discord.Embed(
          title="Invalid Trade",
          description="Sorry! They've already received some of the badges you requested elsewhere while this trade was pending!\n\nTrade has been canceled.",
          color=discord.Color.red()
        )
      )
      try:
        offered_badge_names, requested_badge_names = await get_offered_and_requested_badge_names(active_trade)
        embed = discord.Embed(
          title="Trade Canceled",
          description=f"Just a heads up! Your USS Hood Badge Trade requested from **{requestee.display_name}** was canceled because you already own some of the badges requested!",
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
        return True
      except discord.Forbidden as e:
        logger.info(f"Unable to send trade cancelation message to {requestor.display_name}, they have their DMs closed.")
        pass

    return False


  async def _requestee_already_has_badges(self, interaction, active_trade, requestor, requestee):
    requestee_badges = [b['badge_name'] for b in await db_get_user_badges(active_trade["requestee_id"])]

    trade_offered_badges = await db_get_trade_offered_badges(active_trade)
    trade_offered_badges = [b["badge_name"] for b in trade_offered_badges]

    badges_in_trade_requestee_has = [t for t in requestee_badges if t in trade_offered_badges]

    if len(badges_in_trade_requestee_has) != 0:
      await db_cancel_trade(active_trade)
      await interaction.followup.send(
        embed=discord.Embed(
          title="Invalid Trade",
          description="Sorry! You've already received some of the badges that were offered to you elsewhere while this trade was pending!\n\nTrade has been canceled.",
          color=discord.Color.red()
        )
      )
      try:
        offered_badge_names, requested_badge_names = await get_offered_and_requested_badge_names(active_trade)
        embed = discord.Embed(
          title="Trade Canceled",
          description=f"Just a heads up! Your USS Hood Badge Trade requested from **{requestee.display_name}** was canceled because they already own some of the badges offered!",
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
        return True
      except discord.Forbidden as e:
        logger.info(f"Unable to send trade cancelation message to {requestor.display_name}, they have their DMs closed.")
        pass

    return False

  async def _requestor_still_has_badges(self, interaction, active_trade, requestor, requestee):
    requestor_badges = [b['badge_name'] for b in await db_get_user_badges(active_trade["requestor_id"])]

    trade_offered_badges = await db_get_trade_offered_badges(active_trade)
    trade_offered_badges = [b["badge_name"] for b in trade_offered_badges]

    badges_in_trade_requestor_has = [t for t in requestor_badges if t in trade_offered_badges]

    if len(badges_in_trade_requestor_has) != len(trade_offered_badges):
      await db_cancel_trade(active_trade)
      await interaction.followup.send(
        embed=discord.Embed(
          title="Invalid Trade",
          description="Sorry! They no longer have some the badges they offered!\n\nTrade has been canceled.",
          color=discord.Color.red()
        )
      )
      try:
        offered_badge_names, requested_badge_names = await get_offered_and_requested_badge_names(active_trade)
        embed = discord.Embed(
          title="Trade Canceled",
          description=f"Just a heads up! Your USS Hood Badge Trade requested from **{requestee.display_name}** was canceled because you no longer have some of the badges you offered!",
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
        return False
      except discord.Forbidden as e:
        logger.info(f"Unable to send trade cancelation message to {requestor.display_name}, they have their DMs closed.")
        pass

    return True

  async def _requestee_still_has_badges(self, interaction, active_trade, requestor, requestee):
    requestee_badges = [b["badge_name"] for b in await db_get_user_badges(active_trade["requestee_id"])]

    trade_requested_badges = await db_get_trade_requested_badges(active_trade)
    trade_requested_badges = [b["badge_name"] for b in trade_requested_badges]

    badges_in_trade_requestee_has = [t for t in requestee_badges if t in trade_requested_badges]

    if len(badges_in_trade_requestee_has) != len(trade_requested_badges):
      await db_cancel_trade(active_trade)
      await interaction.followup.send(
        embed=discord.Embed(
          title="Invalid Trade",
          description="Sorry! You no longer have some the badges they requested!\n\nTrade has been canceled.",
          color=discord.Color.red()
        )
      )
      try:
        offered_badge_names, requested_badge_names = await get_offered_and_requested_badge_names(active_trade)
        embed = discord.Embed(
          title="Trade Canceled",
          description=f"Just a heads up! Your USS Hood Badge Trade requested from **{requestee.display_name}** was canceled because they no longer have some of the badges you requested!",
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
        return False
      except discord.Forbidden as e:
        logger.info(f"Unable to send trade cancelation message to {requestor.display_name}, they have their DMs closed.")
        pass

    return True


  async def _decline_trade_callback(self, interaction, active_trade):
    requestor = await self.bot.current_guild.fetch_member(active_trade["requestor_id"])
    requestee = await self.bot.current_guild.fetch_member(active_trade["requestee_id"])

    await interaction.response.edit_message(
      embed=discord.Embed(
        title="Trade Declined",
        description=f"You've declined the proposed trade with **{requestor.display_name}**.\n\nIf their DMs are open, they've been sent a notification to let them know.",
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
        declined_embed = discord.Embed(
          title="Trade Declined",
          description=f"Your USS Hood Badge Trade to **{requestee.display_name}** was declined.",
          color=discord.Color.dark_purple()
        )
        declined_embed.add_field(
          name=f"Offered by {requestor.display_name}",
          value=offered_badge_names
        )
        declined_embed.add_field(
          name=f"Requested from {requestee.display_name}",
          value=requested_badge_names
        )
        declined_embed.set_footer(text="Thank you and have a nice day!")
        await requestor.send(embed=declined_embed)
      except discord.Forbidden as e:
        logger.info(f"Unable to send trade declined message to {requestor.display_name}, they have their DMs closed.")
        pass



  #    ___       _            _             _____            _
  #   / _ \ _  _| |_ __ _ ___(_)_ _  __ _  |_   _| _ __ _ __| |___
  #  | (_) | || |  _/ _` / _ \ | ' \/ _` |   | || '_/ _` / _` / -_)
  #   \___/ \_,_|\__\__, \___/_|_||_\__, |   |_||_| \__,_\__,_\___|
  #                 |___/           |___/
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
    'offer',
    str,
    description="A badge you are offering",
    required=False,
    autocomplete=autocomplete_offering_badges
  )
  @option(
    'request',
    str,
    description="A badge you are requesting",
    required=False,
    autocomplete=autocomplete_requesting_badges
  )
  @commands.check(access_check)
  @commands.check(user_check)
  async def start(self, ctx:discord.ApplicationContext, requestee:discord.User, offer: str, request: str):
    await ctx.defer(ephemeral=True)
    requestor_id = ctx.author.id
    requestee_id = requestee.id

    if not await self._is_trade_initialization_valid(ctx, requestee):
      return

    # If not denied, go ahead and initiate the new trade!
    trade_id = await db_initiate_trade(requestor_id, requestee_id)
    active_trade = {
      'id': trade_id,
      'requestor_id': requestor_id,
      'requestee_id': requestee_id,
    }

    if offer:
      if await self._is_untradeable(ctx, offer, ctx.author, requestee, active_trade, 'offer'):
        offer = None
      else:
        await db_add_badge_to_trade_offer(active_trade, offer)

    if request:
      if await self._is_untradeable(ctx, request, ctx.author, requestee, active_trade, 'request'):
        request = None
      else:
        await db_add_badge_to_trade_request(active_trade, request)


    initiated_trade = await self.check_for_active_trade(ctx)

    # Confirmation of initiation with the requestor
    if not offer and not request:
      follow_up_message = "Follow up with `/trade propose` to fill out the trade details!"
    else:
      follow_up_message = "You can add more badges with `/trade propose`, or you can **Send** / **Cancel** the trade immediately via the buttons below."

    # Paginator Pages
    initiated_embed = discord.Embed(
      title="Trade Started!",
      description=f"Your pending trade has been started!\n\n{follow_up_message}\n\nIf you have additional badges "
                  "you need to offer and request, use \n`/trade send` afterwards to send the trade to the user, "
                  "or to cancel!\n\nNote: You may only have one open outgoing trade request at a time!",
      color=discord.Color.dark_purple()
    ).add_field(
      name="Badges offered by you",
      value=offer
    ).add_field(
      name=f"Badges requested from {requestee.display_name}",
      value=request
    )
    initiated_embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
      icon_url="https://i.imgur.com/GTN4gQG.jpg"
    )

    initiated_image = discord.File(fp="./images/trades/assets/trade_pending.png", filename="trade_pending.png")
    initiated_embed.set_image(url=f"attachment://trade_pending.png")

    initiated_pages = [
      pages.Page(
        embeds=[initiated_embed],
        files=[initiated_image]
      )
    ]

    # Offered page
    offered_embed, offered_image = await self._generate_offered_embed_and_image(initiated_trade)
    initiated_pages.append(
      pages.Page(
        embeds=[offered_embed],
        files=[offered_image]
      )
    )

    # Requested Page
    requested_embed, requested_image = await self._generate_requested_embed_and_image(initiated_trade)
    initiated_pages.append(
      pages.Page(
        embeds=[requested_embed],
        files=[requested_image]
      )
    )

    # Provide Send/Cancel UI immediately
    trade_contains_badges = await does_trade_contain_badges(initiated_trade)
    view = SendCancelView(self, initiated_trade, trade_contains_badges)
    paginator = pages.Paginator(
      pages=initiated_pages,
      use_default_buttons=False,
      custom_buttons=self.trade_buttons,
      custom_view=view,
      loop_pages=True,
      disable_on_timeout=False
    )

    await paginator.respond(ctx.interaction, ephemeral=True)


  @trade.command(
    name="dabo",
    description="Start a randomized trade of unlocked badges with someone (only one outgoing trade active at a time)"
  )
  @option(
    "user",
    discord.User,
    description="The user you wish to start a Dabo trade with",
    required=True
  )
  @option(
    'amount',
    int,
    description="Number of unlocked badges to swap",
    required=True,
    choices=[
      discord.OptionChoice(
        name=str(i),
        value=i
      )
      for i in range(1, 7)
    ]
  )
  @commands.check(access_check)
  @commands.check(user_check)
  async def dabo(self, ctx:discord.ApplicationContext, requestee:discord.User, amount:int):
    await ctx.defer(ephemeral=True)
    requestor_id = ctx.author.id
    requestee_id = requestee.id

    if amount < 1 or amount > 6:
      return

    if not await self._is_trade_initialization_valid(ctx, requestee):
      return

    # Check if either user would go over the badge cap
    max_badge_count = await db_get_max_badge_count()
    requestor_count = await db_get_user_badge_count(requestor_id)
    requestee_count = await db_get_user_badge_count(requestee_id)

    if requestor_count + amount > max_badge_count:
      await ctx.followup.send(embed=discord.Embed(
        title="Trade would exceed badge cap!",
        description=f"Sorry! Receiving {amount} badges would push you over the badge cap ({max_badge_count}).\n\nYou need to give away or unlock more room before doing Dabo.",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    if requestee_count + amount > max_badge_count:
      await ctx.followup.send(embed=discord.Embed(
        title=f"{requestee.display_name} would exceed badge cap!",
        description=f"This Dabo trade would give **{requestee.display_name}** more badges than the total allowed ({max_badge_count}).",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    requestor_total_badges = [b['badge_name'] for b in await db_get_user_badges(requestor_id)]
    requestor_unlocked_badges = [b['badge_name'] for b in await db_get_user_unlocked_badges(requestor_id)]

    requestee_total_badges = [b['badge_name'] for b in await db_get_user_badges(requestee_id)]
    requestee_unlocked_badges = [b['badge_name'] for b in await db_get_user_unlocked_badges(requestee_id)]

    # Get only the badges to offer/request that are not already present in the other user's inventory yet
    valid_requestor_badges = list(np.setdiff1d(requestor_unlocked_badges, requestee_total_badges))
    valid_requestee_badges = list(np.setdiff1d(requestee_unlocked_badges, requestor_total_badges))

    # Check to make sure both parties have enough
    if len(valid_requestor_badges) < amount or len(valid_requestee_badges) < amount:
      not_enough_embed = discord.Embed(
        title="Dabo Denied! Not enough unlocked badges.",
        description=f"Whoops, looks like either you or **{requestee.display_name}** don't have the required number unlocked badges ({amount}) "
                    "to start this trade!\n\nThere either may be not enough total, or not enough that the other user doesn't have already.\n\n"
                    "May need to adjust the amount requested and try again!",
        color=discord.Color.red()
      )
      await ctx.followup.send(embed=not_enough_embed, ephemeral=True)
      return

    # If not denied, go ahead and initiate the new trade!
    trade_id = await db_initiate_trade(requestor_id, requestee_id, 'dabo')
    active_trade = {
      'id': trade_id,
      'requestor_id': requestor_id,
      'requestee_id': requestee_id,
    }

    random_offers = sample(valid_requestor_badges, amount)
    for offer in random_offers:
      await db_add_badge_to_trade_offer(active_trade, offer)

    random_requests = sample(valid_requestee_badges, amount)
    for request in random_requests:
      await db_add_badge_to_trade_request(active_trade, request)

    dabo_trade = await self.check_for_active_trade(ctx)

    # Paginator Pages
    dabo_embed = discord.Embed(
      title="DABO!!!",
      description=f"Your pending dabo trade has been started!\n\n**{amount} randomly selected unlocked badges** from both your inventory, "
                  "and your requestee's inventory each have been added to the trade.\n\nYou may **Send** / **Cancel** now below or use `/trade send` "
                  "to do so later.\n\nNote: Dabo trades count towards only one open outgoing trade request at a time!",
      color=discord.Color.dark_purple()
    ).add_field(
      name="Badges offered by you",
      value="\n".join([f"* {b}" for b in random_offers])
    ).add_field(
      name=f"Badges requested from {requestee.display_name}",
      value="\n".join([f"* {b}" for b in random_requests])
    )
    dabo_embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
      icon_url="https://i.imgur.com/GTN4gQG.jpg"
    )

    dabo_image = discord.File(fp="./images/trades/assets/dabo.png", filename="dabo.png")
    dabo_embed.set_image(url=f"attachment://dabo.png")

    dabo_pages = [
      pages.Page(
        embeds=[dabo_embed],
        files=[dabo_image]
      )
    ]

    # Offered page
    offered_embed, offered_image = await self._generate_offered_embed_and_image(dabo_trade)
    dabo_pages.append(
      pages.Page(
        embeds=[offered_embed],
        files=[offered_image]
      )
    )

    # Requested Page
    requested_embed, requested_image = await self._generate_requested_embed_and_image(dabo_trade)
    dabo_pages.append(
      pages.Page(
        embeds=[requested_embed],
        files=[requested_image]
      )
    )

    # Provide Send/Cancel UI immediately
    trade_contains_badges = await does_trade_contain_badges(dabo_trade)
    view = SendCancelView(self, dabo_trade, trade_contains_badges)
    paginator = pages.Paginator(
      pages=dabo_pages,
      use_default_buttons=False,
      custom_buttons=self.trade_buttons,
      custom_view=view,
      loop_pages=True,
      disable_on_timeout=False
    )

    await paginator.respond(ctx.interaction, ephemeral=True)

  @trade.command(
    name="dtd",
    description="Select a weighted randomized choice from the users opted-in to the Down To Dabo List!"
  )
  @option(
    name="public",
    description="Show to public?",
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
  @commands.check(access_check)
  @commands.check(user_check)
  async def dtd(self, ctx:discord.ApplicationContext, public:str):
    public = bool(public == "yes")

    down_to_daboers = await db_get_dtd_rows()
    if down_to_daboers is None or len(down_to_daboers) == 1:
      await ctx.respond(embed=discord.Embed(
        title="No Down To Daboers Yet!",
        description="No one (else?) has opted-in yet! If you'd like to opt-in, use `/settings`!",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    dtd_userids = []
    dtd_weights = []
    for d in down_to_daboers:
      if int(d['user_discord_id']) != ctx.author.id:
        dtd_userids.append(d['user_discord_id'])
        dtd_weights.append(d['weight'])

    selected_idx = random.choices(range(len(dtd_userids)), weights=dtd_weights)[0]
    selected_user_id = dtd_userids[selected_idx]

    selected_user = self.bot.current_guild.get_member(int(selected_user_id))

    embed = discord.Embed(
      title="Down To Dabo",
      description=f"### {ctx.author.display_name}, your Randomized Down To Daboer is:\n\n"
                  f"- {selected_user.display_name}",
      color=discord.Color.blurple(),
    )
    embed.set_footer(text="You can use `/settings` to opt-in or opt-out of the DTD List!")
    embed.set_image(url="https://i.imgur.com/SnNqoEl.jpg")
    await ctx.respond(embed=embed, ephemeral=not public)
    return

  async def _reset_dtd_weights(self, selected_user_id):
    down_to_daboers = await db_get_dtd_rows()
    dtd_userids = []
    dtd_weights = []
    for d in down_to_daboers:
      dtd_userids.append(d['user_discord_id'])
      dtd_weights.append(d['weight'])

    await db_reset_user_dtd_weight(selected_user_id)
    for i in range(len(dtd_userids)):
      current_user_id = dtd_userids[i]
      if current_user_id != selected_user_id:
        await db_increment_user_dtd_weight(current_user_id)

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

  @trade.command(
    name="send",
    description="Check the current status and send your outgoing trade"
  )
  @commands.check(access_check)
  @commands.check(user_check)
  async def send(self, ctx):
    active_trade = await self.check_for_active_trade(ctx)
    if not active_trade:
      return

    logger.info(f"{Fore.CYAN}{ctx.author.display_name} is checking the status of their current trade.{Style.RESET_ALL}")

    await ctx.defer(ephemeral=True)

    trade_pages = await self._generate_trade_pages(active_trade)
    trade_contains_badges = await does_trade_contain_badges(active_trade)
    view = SendCancelView(self, active_trade, trade_contains_badges)
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
      # Cancel the trade and send confirmation
      await db_cancel_trade(active_trade)
      requestor = await self.bot.current_guild.fetch_member(active_trade["requestor_id"])
      requestee = await self.bot.current_guild.fetch_member(active_trade["requestee_id"])

      confirmation_description = f"Your trade with **{requestee.display_name}** has been canceled!\n\n"
      confirmation_description += "You may now begin a new trade request with `/trade start`"
      confirmation_embed = discord.Embed(
        title="Trade Canceled!",
        description=confirmation_description,
        color=discord.Color.dark_red()
      )
      if active_trade["status"] == 'active':
        confirmation_embed.set_footer(text="Because the trade was active, we've let them know you have canceled the request.")

      await interaction.response.edit_message(
        embed=confirmation_embed,
        view=None,
        attachments=[]
      )

      # Alert the requestee that the trade has been canceled if the trade was active
      user = await get_user(requestee.id)
      if active_trade["status"] == 'active' and user["receive_notifications"]:
        try:
          offered_badge_names, requested_badge_names = await get_offered_and_requested_badge_names(active_trade)

          notification_description = f"Heads up! **{requestor.display_name}** has canceled their pending trade request with you."

          notification_embed = discord.Embed(
            title="Trade Canceled!",
            description=notification_description,
            color=discord.Color.dark_purple()
          )
          notification_embed.add_field(
            name=f"Offered by {requestor.display_name}",
            value=offered_badge_names
          )
          notification_embed.add_field(
            name=f"Requested from {requestee.display_name}",
            value=requested_badge_names
          )
          notification_embed.set_footer(
            text="Note: You can use /settings to enable or disable these messages."
          )

          await requestee.send(embed=notification_embed)
        except discord.Forbidden as e:
          logger.info(f"Unable to send message to trade requestee {requestee.display_name} because they have DMs disabled.")
          pass
    except Exception as e:
      logger.info(traceback.format_exc())

  async def _send_trade_callback(self, interaction, active_trade):
    try:
      if not await does_trade_contain_badges(active_trade):
        await interaction.response.edit_message(
          embed=discord.Embed(
            title="Invalid Trade",
            description="You must use `/trade propose` to include at least one badge before sending a request.",
            color=discord.Color.red()
          ),
          view=None,
          attachments=[]
        )
        return

      # Activate the trade and send confirmation
      await db_activate_trade(active_trade)
      requestor = await self.bot.current_guild.fetch_member(active_trade["requestor_id"])
      requestee = await self.bot.current_guild.fetch_member(active_trade["requestee_id"])

      logger.info(f"{Fore.CYAN}{requestor.display_name} has activated a trade with {requestee.display_name}{Style.RESET_ALL}")

      await interaction.response.edit_message(
        embed=discord.Embed(
          title="Trade Sent!",
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

      if active_trade['type'] == 'dabo' and await db_is_user_in_dtd_list(active_trade["requestee_id"]):
        await self._reset_dtd_weights(active_trade["requestee_id"])

      # Give notice to Requestee
      user = await get_user(requestee.id)
      if user["receive_notifications"]:
        try:
          offered_badge_names, requested_badge_names = await get_offered_and_requested_badge_names(active_trade)

          if active_trade['type'] == 'dabo':
            title = "INCOMING DABO!"
            description = f"Heya, **{requestor.display_name}** has initiated a randomized trade of unlocked badges with you on The USS Hood.\n\n**DABO!!!**\n\n"
          else:
            title = "Trade Offered"
            description = f"Hey there, wanted to let you know that **{requestor.display_name}** has requested a trade from you on The USS Hood.\n\n"

          description += f"Use `/trade incoming` in the channel to review and either accept or deny!\n\nYou can jump to their offer directly at at {home_message.jump_url}!"

          requestee_embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.dark_purple()
          )
          requestee_embed.add_field(
            name=f"Offered by {requestor.display_name}",
            value=offered_badge_names
          )
          requestee_embed.add_field(
            name=f"Requested from {requestee.display_name}",
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

    offered_badges = await db_get_trade_offered_badges(active_trade)
    offered_badge_filenames = [f"{b['badge_filename']}" for b in offered_badges]
    offered_image_id = f"{active_trade['id']}-offered"
    offered_image = await generate_badge_trade_showcase(
      offered_badge_filenames,
      offered_image_id,
      f"Badge(s) Offered by {requestor.display_name}",
      f"{len(offered_badge_filenames)} Badges"
    )
    offered_embed = discord.Embed(
      title="Offered",
      description=f"Badges offered by **{requestor.display_name}** to **{requestee.display_name}**",
      color=discord.Color.dark_purple()
    )
    offered_embed.set_image(url=f"attachment://{offered_image_id}.png")

    return offered_embed, offered_image

  async def _generate_requested_embed_and_image(self, active_trade):
    requestee = await self.bot.current_guild.fetch_member(active_trade["requestee_id"])
    requestor = await self.bot.current_guild.fetch_member(active_trade["requestor_id"])

    requested_badges = await db_get_trade_requested_badges(active_trade)
    requested_badge_filenames = [f"{b['badge_filename']}" for b in requested_badges]
    requested_image_id = f"{active_trade['id']}-requested"
    requested_image = await generate_badge_trade_showcase(
      requested_badge_filenames,
      requested_image_id,
      f"Badge(s) Requested from {requestee.display_name}",
      f"{len(requested_badge_filenames)} Badges"
    )
    requested_embed = discord.Embed(
      title="Requested",
      description=f"Badges requested from **{requestee.display_name}** by **{requestor.display_name}**",
      color=discord.Color.dark_purple()
    )
    requested_embed.set_image(url=f"attachment://{requested_image_id}.png")

    return requested_embed, requested_image

  async def _generate_home_embed_and_image(self, active_trade):
    requestor = await self.bot.current_guild.fetch_member(active_trade["requestor_id"])
    requestee = await self.bot.current_guild.fetch_member(active_trade["requestee_id"])

    offered_badge_names, requested_badge_names = await get_offered_and_requested_badge_names(active_trade)

    if active_trade["status"] == 'active':
      color = discord.Color.dark_purple()
      if active_trade["type"] == 'dabo':
        title = "DABO TRADE!!!"
        description=f"A randomized trade of unlocked badges!\n\n**{requestor.display_name}** has offered a Dabo Trade to **{requestee.display_name}**!\n## DABO!!!"
        image_filename = "dabo.png"
      else:
        title = "Trade Offered!"
        description = f"Get that, get that, gold pressed latinum!\n\n**{requestor.display_name}** has offered a trade to **{requestee.display_name}**!"
        image_filename = "trade_offer.png"

    elif active_trade["status"] == 'pending':
      color = discord.Color(0x99aab5)
      if active_trade["type"] == 'dabo':
        title = "DABO PENDING!!!"
        description=f"You've initiated a randomized trade of unlocked badges!\n\nThis your pending Dabo trade with **{requestee.display_name}**!\n## DABO!!!"
        image_filename = "dabo.png"
      else:
        title = "Trade Pending..."
        description = f"Ready to send?\n\nThis your pending trade with **{requestee.display_name}**.\n\n"
        if await does_trade_contain_badges(active_trade):
          description += "Press the Send button below if it looks good to go!"
        else:
          description += "You'll need to include at least one badge as either offered or requested to proceed!"
        image_filename = "trade_pending.png"

    home_embed = discord.Embed(
      title=title,
      description=description,
      color=color
    )
    home_embed.add_field(
      name=f"Offered by {requestor.display_name}",
      value=offered_badge_names
    )
    home_embed.add_field(
      name=f"Requested from {requestee.display_name}",
      value=requested_badge_names
    )
    home_embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
      icon_url="https://i.imgur.com/GTN4gQG.jpg"
    )
    home_image = discord.File(fp=f"./images/trades/assets/{image_filename}", filename=image_filename)
    home_embed.set_image(url=f"attachment://{image_filename}")

    return home_embed, home_image

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
    autocomplete=autocomplete_requesting_badges
  )
  @commands.check(access_check)
  @commands.check(user_check)
  async def propose(self, ctx, offer:str, request:str):
    active_trade = await self.check_for_active_trade(ctx)
    if not active_trade:
      return

    if active_trade['type'] == 'dabo':
      await ctx.respond(embed=discord.Embed(
        title=f"Dabo Trades Are Not Modifiable",
        description=f"You can however cancel the trade via the `/trade send` interface and generate a new one if needed.",
        color=discord.Color.dark_red()
      ), ephemeral=True)
      return

    if offer:
      await self._add_offered_badge_to_trade(ctx, active_trade, offer)
    if request:
      await self._add_requested_badge_to_trade(ctx, active_trade, request)
    if not offer and not request:
      await ctx.respond(embed=discord.Embed(
        title=f"Please select a badge to offer or trade",
        description=f"If you want to update your trade, you need to give a badge",
        color=discord.Color.dark_red()
      ), ephemeral=True)

  async def _add_offered_badge_to_trade(self, ctx, active_trade, badge):
    """ Offer the badge or reply with error message """
    # Don't need to check for active because already done so in propose()
    requestee = await self.bot.current_guild.fetch_member(active_trade["requestee_id"])
    requestor = await self.bot.current_guild.fetch_member(active_trade["requestor_id"])

    logger.info(f"{Fore.CYAN}{requestor.display_name} is looking to offer `{badge}` to {requestee.display_name}.")

    if await self._is_untradeable(ctx, badge, requestor, requestee, active_trade, 'offer'):
      return

    await db_add_badge_to_trade_offer(active_trade, badge)
    logger.info(f"{Fore.CYAN}{requestor.display_name} has added the badge `{badge}` to their pending trade offer to {requestee.display_name}{Style.RESET_ALL}")

    badge_info = await db_get_badge_info_by_name(badge)
    badge_filename = badge_info['badge_filename']
    discord_image = discord.File(fp=f"./images/badges/{badge_filename}", filename=badge_filename)

    badge_offered_embed = discord.Embed(
      title=f"{badge} added to offer.",
      description=f"This badge has been added to your offer to **{requestee.display_name}**",
      color=discord.Color.dark_green()
    )
    badge_offered_embed.set_image(url=f"attachment://{badge_filename}")
    await ctx.respond(embed=badge_offered_embed, file=discord_image, ephemeral=True)

  async def _add_requested_badge_to_trade(self, ctx, active_trade, badge):
    """ Request the badge or reply with error message """
    # Don't need to check for active because already done so in propose()
    requestee = await self.bot.current_guild.fetch_member(active_trade["requestee_id"])
    requestor = await self.bot.current_guild.fetch_member(active_trade["requestor_id"])

    logger.info(f"{Fore.CYAN}{requestor.display_name} is looking to request `{badge}` from {requestee.display_name}.")

    if await self._is_untradeable(ctx, badge, requestor, requestee, active_trade, 'request'):
      return

    await db_add_badge_to_trade_request(active_trade, badge)
    logger.info(f"{Fore.CYAN}{requestor.display_name} has added the badge `{badge}` to their pending trade request from {requestee.display_name}{Style.RESET_ALL}")

    badge_info = await db_get_badge_info_by_name(badge)
    badge_filename = badge_info['badge_filename']
    discord_image = discord.File(fp=f"./images/badges/{badge_filename}", filename=badge_filename)

    addition_embed = discord.Embed(
      title=f"{badge} added to request.",
      description=f"This badge has been added to your request from **{requestee.display_name}**",
      color=discord.Color.dark_green()
    )
    addition_embed.set_image(url=f"attachment://{badge_filename}")
    await ctx.respond(embed=addition_embed, file=discord_image, ephemeral=True)

  async def _is_untradeable(self, ctx: discord.ApplicationContext, badge: str, requestor: discord.User, requestee: discord.User, active_trade, direction="either 'offer' or 'request'") -> bool:
    """
    Test this badge to see if it can be added to the trade.  If it can't, show the user an error message.  It’s a
    little complicated because the logic and language changes based on if the badge is going from the user making the
    request or not. But this is still better than ^C^V the next error that comes up.
    """
    if direction == 'offer':
      dir_preposition = 'to'
      to_user = requestee
      from_user = requestor
    else:
      dir_preposition = 'from'
      to_user = requestor
      from_user = requestee

    if badge in [b['badge_name'] for b in await db_get_special_badges()]:
      logger.info(f"{Fore.CYAN}{requestor.display_name} tried to {direction} `{badge}` {dir_preposition} "
                  f"{requestee.display_name} but it's untradeable!")
      await ctx.respond(embed=discord.Embed(
        title="That badge is untradeable!",
        description=f"Sorry, you can't request `{badge}`! It's a very shiny and special one!",
        color=discord.Color.red()
      ), ephemeral=True)
      return True

    user_badges = [b["badge_name"] for b in await db_get_user_badges(from_user.id)]
    if badge not in user_badges:
      logger.info(f"{Fore.CYAN}{from_user.display_name} doesn't possess `{badge}`, unable to add to {direction} "
                  f"{dir_preposition} {to_user.display_name}.")
      await ctx.respond(embed=discord.Embed(
        title=f"{'You' if direction == 'offer' else 'They'} do not possess that badge",
        description=f"`{badge}` does not match any badges {'you' if direction == 'offer' else 'they'} possess.\n\n"
                    f"You can use the autocomplete in the query to find the badges "
                    f"{'you' if direction == 'offer' else 'they'} do have!",
        color=discord.Color.red()
      ), ephemeral=True)
      return True

    user_badges = [b["badge_name"] for b in await db_get_user_badges(to_user.id)]
    if badge in user_badges:
      logger.info(f"{Fore.CYAN}{requestor.display_name} was unable to add `{badge}` to their pending trade {direction} "
                  f"{dir_preposition} {requestee.display_name} because {to_user.display_name} already owns the badge! "
                  f"No action taken.{Style.RESET_ALL}")
      await ctx.respond(embed=discord.Embed(
        title=f"{'You' if direction == 'request' else 'They'} already have {badge}!",
        description=f"No need to {direction} this one!",
        color=discord.Color.red()
      ), ephemeral=True)
      return True

    trade_badges = (await db_get_trade_offered_badges(active_trade)
                    if direction == 'offer' else
                    await db_get_trade_requested_badges(active_trade))
    trade_badge_names = [b["badge_name"] for b in trade_badges]

    if badge in trade_badge_names:
      logger.info(f"{Fore.CYAN}{requestor.display_name} already had badge `{badge}` present in their pending trade "
                  f"{direction} {dir_preposition} {requestee.display_name}. No action taken.{Style.RESET_ALL}")
      await ctx.respond(embed=discord.Embed(
        title=f"{badge} already exists in {direction}.",
        description="No action taken.",
        color=discord.Color.red()
      ), ephemeral=True)
      return True

    if len(trade_badges) >= self.max_badges_per_trade:
      logger.info(f"{Fore.CYAN}{requestor.display_name} was unable to add `{badge}` to their pending trade "
                  f"{direction} {dir_preposition} {requestee.display_name} because the trade is already at the maximum "
                  f"number of offers allowed: {self.max_badges_per_trade}. No action taken.{Style.RESET_ALL}")
      await ctx.respond(embed=discord.Embed(
        title=f"Unable to add {badge} to offer.",
        description=f"You're at the max number of badges allowed per trade ({self.max_badges_per_trade})!",
        color=discord.Color.red()
      ), ephemeral=True)
      return True

    # Check to make sure the receiving user wouldn't go over the badge cap limit
    max_badge_count = await db_get_max_badge_count()
    to_user_badge_count = await db_get_user_badge_count(to_user.id)
    if direction == 'offer':
      incoming_badges = await db_get_trade_offered_badges(active_trade)
    else:
      incoming_badges = await db_get_trade_requested_badges(active_trade)

    if to_user_badge_count + len(incoming_badges) + 1 > max_badge_count:
      await ctx.respond(embed=discord.Embed(
        title=f"{to_user.display_name} is at the badge cap!",
        description=f"Adding `{badge}` would exceed the total number of badges which exist ({max_badge_count}).\n\nY'all badgers got too many badges yo, give some away or something.",
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

# ________                      .__
# \_____  \  __ __   ___________|__| ____   ______
#  /  / \  \|  |  \_/ __ \_  __ \  |/ __ \ /  ___/
# /   \_/.  \  |  /\  ___/|  | \/  \  ___/ \___ \
# \_____\ \_/____/  \___  >__|  |__|\___  >____  >
#        \__>           \/              \/     \/
async def db_add_badge_to_trade_offer(active_trade, badge_name):
  active_trade_id = active_trade["id"]
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      INSERT INTO trade_offered (trade_id, badge_filename)
        VALUES (%s, (SELECT badge_filename FROM badge_info WHERE badge_name = %s))
    '''
    vals = (active_trade_id, badge_name)
    await query.execute(sql, vals)

async def db_remove_badge_from_trade_offer(active_trade, badge_name):
  active_trade_id = active_trade["id"]
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      DELETE FROM trade_offered
        WHERE trade_id = %s AND badge_filename = (SELECT badge_filename FROM badge_info WHERE badge_name = %s)
    '''
    vals = (active_trade_id, badge_name)
    await query.execute(sql, vals)

async def db_add_badge_to_trade_request(active_trade, badge_name):
  active_trade_id = active_trade["id"]
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      INSERT INTO trade_requested (trade_id, badge_filename)
        VALUES (%s, (SELECT badge_filename FROM badge_info WHERE badge_name = %s))
    '''
    vals = (active_trade_id, badge_name)
    await query.execute(sql, vals)

async def db_remove_badge_from_trade_request(active_trade, badge_name):
  active_trade_id = active_trade["id"]
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      DELETE FROM trade_requested
        WHERE trade_id = %s AND badge_filename = (SELECT badge_filename FROM badge_info WHERE badge_name = %s)
    '''
    vals = (active_trade_id, badge_name)
    await query.execute(sql, vals)

async def db_get_active_requestee_trades(requestee_id):
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT * FROM trades WHERE requestee_id = %s AND status = 'active'"
    vals = (requestee_id,)
    await query.execute(sql, vals)
    trades = await query.fetchall()
  return trades

async def db_get_active_requestor_trade(requestor_id):
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT * FROM trades WHERE requestor_id = %s AND (status = 'active' OR status = 'pending') LIMIT 1"
    vals = (requestor_id,)
    await query.execute(sql, vals)
    trade = await query.fetchone()
  return trade

async def db_get_active_trade_between_requestor_and_requestee(requestor_id, requestee_id):
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT * FROM trades WHERE requestor_id = %s AND requestee_id = %s AND status = 'active' LIMIT 1"
    vals = (requestor_id, requestee_id)
    await query.execute(sql, vals)
    trade = await query.fetchone()
  return trade

async def db_initiate_trade(requestor_id:int, requestee_id:int, type="standard") -> int:
  async with AgimusDB() as query:
    sql = "INSERT INTO trades (requestor_id, requestee_id, status, type) VALUES (%s, %s, 'pending', %s)"
    vals = (requestor_id, requestee_id, type)
    await query.execute(sql, vals)
    result = query.lastrowid
  return result

async def db_activate_trade(active_trade):
  active_trade_id = active_trade["id"]
  async with AgimusDB() as query:
    sql = "UPDATE trades SET status = 'active' WHERE id = %s"
    vals = (active_trade_id,)
    await query.execute(sql, vals)

async def db_cancel_trade(trade):
  trade_id = trade['id']
  async with AgimusDB() as query:
    sql = "UPDATE trades SET status = 'canceled' WHERE id = %s"
    vals = (trade_id,)
    await query.execute(sql, vals)

async def db_perform_badge_transfer(active_trade):
  trade_id = active_trade['id']
  requestor_id = active_trade['requestor_id']
  requestee_id = active_trade['requestee_id']
  async with AgimusDB(dictionary=True) as query:

    # Transfer Requested Badges to Requestor
    sql = '''
      INSERT INTO badges (user_discord_id, badge_filename)
        SELECT t.requestor_id, b_i.badge_filename
          FROM trades as t
          JOIN badge_info as b_i
          JOIN trade_requested as t_r
            ON t.id = %s AND t_r.trade_id = t.id AND t_r.badge_filename = b_i.badge_filename
    '''
    vals = (trade_id,)
    await query.execute(sql, vals)

    # Delete Requested Badges from Requestee
    sql = '''
      DELETE b FROM badges b
        JOIN badge_info b_i ON b.badge_filename = b_i.badge_filename
        JOIN trade_requested t_r ON t_r.badge_filename = b_i.badge_filename
        JOIN trades t ON t_r.trade_id = t.id
          WHERE (t.id = %s AND t.requestee_id = %s AND b.user_discord_id = %s)
    '''
    vals = (trade_id, requestee_id, requestee_id)
    await query.execute(sql, vals)

    # Transfer Offered Badges to Requestee
    sql = '''
      INSERT INTO badges (user_discord_id, badge_filename)
        SELECT t.requestee_id, b_i.badge_filename
          FROM trades as t
          JOIN badge_info as b_i
          JOIN trade_offered as t_o
            ON t.id = %s AND t_o.trade_id = t.id AND t_o.badge_filename = b_i.badge_filename
    '''
    vals = (trade_id,)
    await query.execute(sql, vals)

    # Delete Offered Badges from Requestor
    sql = '''
      DELETE b FROM badges b
        JOIN badge_info b_i ON b.badge_filename = b_i.badge_filename
        JOIN trade_offered t_o ON t_o.badge_filename = b_i.badge_filename
        JOIN trades t ON t_o.trade_id = t.id
          WHERE (t.id = %s AND t.requestor_id = %s AND b.user_discord_id = %s)
    '''
    vals = (trade_id, requestor_id, requestor_id)
    await query.execute(sql, vals)

async def db_complete_trade(active_trade):
  trade_id = active_trade['id']
  async with AgimusDB() as query:
    sql = "UPDATE trades SET status = 'complete' WHERE id = %s"
    vals = (trade_id,)
    await query.execute(sql, vals)

async def db_decline_trade(active_trade):
  trade_id = active_trade['id']
  async with AgimusDB() as query:
    sql = "UPDATE trades SET status = 'declined' WHERE id = %s"
    vals = (trade_id,)
    await query.execute(sql, vals)

async def db_get_related_badge_trades(active_trade):
  active_trade_id = active_trade["id"]
  async with AgimusDB(dictionary=True) as query:
    # All credit for this query to Danma! Praise be!!!
    sql = '''
      SELECT t.*

      FROM trades as t
      LEFT JOIN trade_offered `to` ON t.id = to.trade_id
      LEFT JOIN trade_requested `tr` ON t.id = tr.trade_id

      INNER JOIN (
          SELECT trade_id, requestor_id, requestee_id, badge_filename
          FROM trade_requested
          INNER JOIN trades ON trade_requested.trade_id = trades.id AND trades.id = %s
          UNION ALL
          SELECT trade_id, requestor_id, requestee_id, badge_filename
          FROM trade_offered
          INNER JOIN trades ON trade_offered.trade_id = trades.id AND trades.id = %s
      ) as activeTrade ON 1

      -- not the active trade
      WHERE t.id != activeTrade.trade_id

      -- pending or active
      AND t.status IN ('pending','active')

      -- involves one or more of the users involved in the active trade
      AND (t.requestor_id IN (activeTrade.requestor_id, activeTrade.requestee_id) OR t.requestee_id IN (activeTrade.requestor_id, activeTrade.requestee_id))

      -- involves one or more of the badges involved in the active trade
      AND (to.badge_filename = activeTrade.badge_filename OR tr.badge_filename = activeTrade.badge_filename)
      GROUP BY t.id
    '''
    vals = (active_trade_id, active_trade_id)
    await query.execute(sql, vals)
    trades = await query.fetchall()
  return trades

async def db_is_user_in_dtd_list(user_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT user_discord_id FROM down_to_dabo WHERE user_discord_id = %s LIMIT 1"
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    id = await query.fetchone()
  return id

async def db_get_dtd_rows():
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT * FROM down_to_dabo"
    await query.execute(sql)
    rows = await query.fetchall()
  return rows

async def db_reset_user_dtd_weight(selected_user_id):
  async with AgimusDB() as query:
    sql = "UPDATE down_to_dabo SET weight = 1 WHERE user_discord_id = %s"
    vals = (selected_user_id,)
    await query.execute(sql, vals)

async def db_increment_user_dtd_weight(user_discord_id):
  async with AgimusDB() as query:
    sql = "UPDATE down_to_dabo SET weight = weight + 1 WHERE user_discord_id = %s"
    vals = (user_discord_id,)
    await query.execute(sql, vals)
