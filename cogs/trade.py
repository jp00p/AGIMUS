from common import *
from utils.badge_utils import generate_badge_trade_showcase
from utils.check_channel_access import access_check

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
async def autocomplete_requestor_badges(ctx:discord.AutocompleteContext):
  requestor_badges = db_get_user_badge_names(ctx.interaction.user.id)
  autocomplete_results = []
  for badge in requestor_badges:
    badge_name = badge["badge_name"].replace(".png", "").replace("_", " ")
    autocomplete_results.append(badge_name)
  return [result for result in autocomplete_results if ctx.value.lower() in result.lower()]

async def autocomplete_requestee_badges(ctx:discord.AutocompleteContext):
  active_trade = db_get_active_requestor_trade(ctx.interaction.user.id)
  if not active_trade:
    return []
  requestee_badges = db_get_user_badge_names(active_trade['requestee_id'])
  autocomplete_results = []
  for badge in requestee_badges:
    badge_name = badge["badge_name"].replace(".png", "").replace("_", " ")
    autocomplete_results.append(badge_name)
  return [result for result in autocomplete_results if ctx.value.lower() in result.lower()]


# ____   ____.__
# \   \ /   /|__| ______  _  ________
#  \   Y   / |  |/ __ \ \/ \/ /  ___/
#   \     /  |  \  ___/\     /\___ \
#    \___/   |__|\___  >\/\_//____  >
#                    \/           \/
class SendConfirmView(discord.ui.View):
  def __init__(self, cog):
    super().__init__()
    self.value = None

  @discord.ui.button(label="    Cancel    ", style=discord.ButtonStyle.grey)
  async def cancel_callback(self, button:discord.ui.Button, interaction:discord.Interaction):
    self.disable_all_items()
    await interaction.response.edit_message(view=self)
    self.value = False
    self.stop()

  @discord.ui.button(label="    Confirm    ", style=discord.ButtonStyle.green)
  async def confirm_callback(self, button:discord.ui.Button, interaction:discord.Interaction):
    self.disable_all_items()
    await interaction.response.edit_message(view=self)
    self.value = True
    self.stop()


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
      await self.cog._send_trade_interface(interaction, requestor)

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
      style=discord.ButtonStyle.success,
      row=2
    )

  async def callback(self, interaction: discord.Interaction):
    view = self.view
    view.disable_all_items()
    await interaction.response.edit_message(view=view)
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
    self.max_trades = 3
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
    name="reply",
    description="View and accept/decline incoming trades from other users"
  )
  @commands.check(access_check)
  async def reply(self, ctx:discord.ApplicationContext):
    incoming_trades = db_get_active_requestee_trades(ctx.user.id)

    if not incoming_trades:
      await ctx.respond(embed=discord.Embed(
          title="No Incoming Trade Requests",
          description="No one has any active trades requested from you. Get out there are start hustlin!",
          color=discord.Color.blurple()
        ),
        ephemeral=True
      )
      return

    incoming_requestor_ids = [t["requestor_id"] for t in incoming_trades]
    requestors = []
    for user_id in incoming_requestor_ids:
      requestor = await self.bot.fetch_user(user_id)
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

  async def _send_trade_interface(self, interaction, requestor_id):
    requestee_id = interaction.user.id
    active_trade = db_get_active_trade_between_requestor_and_requestee(requestor_id, requestee_id)

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

    # Perform the actual swap
    db_perform_badge_transfer(active_trade)
    db_complete_trade(active_trade)

    # Send Message to Channel
    requestor = await self.bot.fetch_user(active_trade["requestor_id"])
    requestee = await self.bot.fetch_user(active_trade["requestee_id"])

    offered_badge_names, requested_badge_names = await self._get_offered_and_requested_badge_names(active_trade)

    success_embed = discord.Embed(
      title="Successful Trade!",
      description=f"{requestor.mention} and {requestee.mention} came to an agreement!\n\nBadges transferred successfully!",
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
    success_image = discord.File(fp="./images/trades/assets/trade_successful.jpg", filename="trade_successful.jpg")
    success_embed.set_image(url=f"attachment://trade_successful.jpg")
    success_embed.set_footer(text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}")

    channel = interaction.channel
    await channel.send(embed=success_embed, file=success_image)

    # Send notification to requestor the the trade was successful
    user = get_user(requestor.id)
    if user["receive_notifications"]:
      try:
        await requestor.send(embed=success_embed)
      except discord.Forbidden as e:
        logger.info(f"Unable to send trade cancelation message to {requestor.display_name}, they have their DMs closed.")
        pass


  async def _cancel_invalid_related_trades(self, active_trade):
    # These are all the active or pending trades that involved either the requestee or
    # requestor and include the badges that are involved with the confirmed trade which
    # are thus no longer valid and need to be canceled
    related_trades = db_get_related_badge_trades(active_trade)
    logger.info("related trades:")
    logger.info(pprint(related_trades))

    # Filter out the current trade itself, then cancel the others
    trades_to_cancel = [t for t in related_trades if t["id"] != active_trade["id"]]

    # Iterate through to cancel, and then
    for trade in trades_to_cancel:
      db_cancel_trade(trade)
      requestee = await self.bot.fetch_user(trade['requestee_id'])
      requestor = await self.bot.fetch_user(trade['requestor_id'])

      offered_badge_names, requested_badge_names = await self._get_offered_and_requested_badge_names(trade)

      # Give notice to Requestee
      user = get_user(requestee.id)
      if user["receive_notifications"]:
        try:
          requestee_embed = discord.Embed(
            title="Trade Canceled",
            description=f"Just a heads up! Your USS Hood Badge Trade initiated by {requestor.mention} was canceled because one or more of the badges involved were traded to another user.",
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
          requestee_embed.set_footer(text="Thank you and have a nice day!")
          await requestee.send(embed=requestee_embed)
        except discord.Forbidden as e:
          logger.info(f"Unable to send trade cancelation message to {requestee.display_name}, they have their DMs closed.")
          pass

      # Give notice to Requestor
      user = get_user(requestor.id)
      if user["receive_notifications"]:
        try:
          requestor_embed = discord.Embed(
            title="Trade Canceled",
            description=f"Just a heads up! Your USS Hood Badge Trade requested from {requestee.mention} was canceled because one or more of the badges involved were traded to another user.",
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
          requestor_embed.set_footer(text="Thank you and have a nice day!")
          await requestor.send(embed=requestor_embed)
        except discord.Forbidden as e:
          logger.info(f"Unable to send trade cancelation message to {requestor.display_name}, they have their DMs closed.")
          pass

  async def _decline_trade_callback(self, interaction, active_trade):
    requestor = await self.bot.fetch_user(active_trade["requestor_id"])
    requestee = await self.bot.fetch_user(active_trade["requestee_id"])

    await interaction.response.edit_message(
      embed=discord.Embed(
        title="Trade Declined",
        description=f"You've declined the proposed trade with {requestor.mention}.\n\nIf their DMs are open, they've been sent a notification to let them know.",
        color=discord.Color.blurple()
      ),
      view=None
    )

    db_decline_trade(active_trade)
    offered_badge_names, requested_badge_names = await self._get_offered_and_requested_badge_names(active_trade)

    user = get_user(requestor.id)
    if user["receive_notifications"]:
      try:
        declined_embed = discord.Embed(
          title="Trade Declined",
          description=f"Your USS Hood Badge Trade to {requestee.mention} was declined.",
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
    name="initiate",
    description="Initiate a trade with a specified user (only one outgoing trade active at a time)"
  )
  @option(
    "user",
    discord.User,
    description="The user you wish to initiate a trade with",
    required=True
  )
  @commands.check(access_check)
  async def initiate(self, ctx:discord.ApplicationContext, requestee:discord.User):
    try:
      requestor_id = ctx.author.id
      requestee_id = requestee.id

      if requestor_id == requestee_id:
        await ctx.respond(embed=discord.Embed(
          title="Don't be silly!",
          description="You can't request a trade from yourself!",
          color=discord.Color.red()
        ), ephemeral=True)
        return

      if requestee_id == self.bot.user.id:
        await ctx.respond(embed=discord.Embed(
          title="Nope",
          description="AGIMUS has no badges to trade!",
          color=discord.Color.red()
        ), ephemeral=True)
        return

      # Deny requests to users that do not have XP enabled
      requestee_details = get_user(requestee_id)
      if not requestee_details or not requestee_details["xp_enabled"]:
        opted_out_embed = discord.Embed(
          title="This user is not participating.",
          description=f"Sorry, {requestee.mention} has opted out of the XP system and is not available for trading.",
          color=discord.Color.red()
        )
        await ctx.respond(embed=opted_out_embed, ephemeral=True)
        return

      # Deny the trade request if there's an existing trade in progress by the requestor
      active_trade = db_get_active_requestor_trade(requestor_id)
      if active_trade:
        active_trade_requestee = await self.bot.fetch_user(active_trade['requestee_id'])
        already_active_embed = discord.Embed(
          title="You already have an active trade!",
          description=f"You have a outgoing trade open with {active_trade_requestee.mention}.\n\nUse `/trade status` to view this current trade.\nUse `/trade cancel` to close the current trade if desired!\n\nThis must be resolved before you can open another request.",
          color=discord.Color.red()
        )
        already_active_embed.set_footer(text="You may want to check on this trade to see if they have had a chance to review your request!")
        await ctx.respond(embed=already_active_embed, ephemeral=True)
        return

      # Deny the trade request if the requestee already has too many active trades pending
      requestee_trades = db_get_active_requestee_trades(requestee_id)
      if len(requestee_trades) >= self.max_trades:
        max_requestee_trades_embed = discord.Embed(
          title=f"{requestee.display_name} has too many pending trades!",
          description=f"Sorry, the person you've requested a trade from already has the maximum number of trade requests pending ({self.max_trades}).",
          color=discord.Color.red()
        )
        await ctx.respond(embed=max_requestee_trades_embed, ephemeral=True)
        return

      # If not denied, go ahead and initiate the new trade!
      db_initiate_trade(requestor_id, requestee_id)

      # Confirmation of initiation with the requestor
      initiated_embed = discord.Embed(
        title="Trade Initiated!",
        description="Your pending trade has been initiated!\n\nFollow up with `/trade request` and `/trade offer` to fill out the trade details!\n\nOnce you have added the badges you'd like to offer and request, use \n`/trade activate` to send the trade to the user!\n\nUse `/trade cancel` if you wish to dismiss the current trade.\n\nNote: You may only have one open outgoing trade request at a time!",
        color=discord.Color.dark_purple()
      ).add_field(
        name="Requested By (You)",
        value=f"{ctx.author.mention}"
      ).add_field(
        name="Requested From",
        value=f"{requestee.mention}"
      )
      initiated_embed.set_footer(text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}")
      await ctx.respond(embed=initiated_embed, ephemeral=True)

    except Exception as e:
      logger.info(traceback.format_exc())


  @trade.command(
    name="cancel",
    description="Cancel your currently active or pending outgoing trade"
  )
  @option(
    name="reason",
    description="Reason for canceling?",
    required=False
  )
  @commands.check(access_check)
  async def cancel(self, ctx:discord.ApplicationContext, reason:str):
    try:
      active_trade = await self.check_for_active_trade(ctx)
      if not active_trade:
        return

      # Otherwise, cancel the trade and send confirmation
      db_cancel_trade(active_trade)
      requestor = await self.bot.fetch_user(active_trade["requestor_id"])
      requestee = await self.bot.fetch_user(active_trade["requestee_id"])

      confirmation_description = f"Your trade with {requestee.mention} has been canceled!\n\n"
      if reason:
        confirmation_description += f"**Reason:** {reason}\n\n"
      confirmation_description += "You may now begin a new trade request with `/trade initiate`"
      confirmation_embed = discord.Embed(
        title="Trade Canceled!",
        description=confirmation_description,
        color=discord.Color.dark_red()
      )
      if active_trade["status"] == 'active':
        confirmation_embed.set_footer(text="Because the trade was active, we've let them know you have canceled the request.")
      await ctx.respond(embed=confirmation_embed, ephemeral=True)

      # Alert the requestee that the trade has been canceled if the trade was active
      user = get_user(requestee.id)
      if active_trade["status"] == 'active' and user["receive_notifications"]:
        try:
          offered_badge_names, requested_badge_names = await self._get_offered_and_requested_badge_names(active_trade)

          notification_description = f"Heads up! {requestor.mention} has canceled their pending trade request with you."
          if reason:
            notification_description += f"\n\n**Reason:** {reason}"

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

          await requestee.send(embed=notification_embed)
        except discord.Forbidden as e:
          logger.info(f"Unable to send message to trade requestee {requestee.display_name} because they have DMs disabled.")
          pass
    except Exception as e:
      logger.info(traceback.format_exc())


  @trade.command(
    name="status",
    description="Check the current status of your outgoing trade"
  )
  @commands.check(access_check)
  async def status(self, ctx):
    active_trade = await self.check_for_active_trade(ctx)
    if not active_trade:
      return

    logger.info(f"{Fore.CYAN}{ctx.author.display_name} is checking the status of their current trade.{Style.RESET_ALL}")

    await ctx.defer(ephemeral=True)

    trade_pages = await self._generate_trade_pages(active_trade)
    paginator = pages.Paginator(
      pages=trade_pages,
      use_default_buttons=False,
      custom_buttons=self.trade_buttons,
      loop_pages=True,
      timeout=720
    )

    await paginator.respond(ctx.interaction, ephemeral=True)

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
    requestee = await self.bot.fetch_user(active_trade["requestee_id"])
    requestor = await self.bot.fetch_user(active_trade["requestor_id"])

    offered_badges = db_get_trade_offered_badges(active_trade)
    offered_badge_filenames = [f"{b['badge_name'].replace(' ', '_')}.png" for b in offered_badges]
    offered_image_id = f"{active_trade['id']}-offered"
    offered_image = generate_badge_trade_showcase(
      offered_badge_filenames,
      offered_image_id,
      f"Badge(s) Offered by {requestor.display_name}",
      f"{len(offered_badge_filenames)} Badges"
    )
    offered_embed = discord.Embed(
      title="Offered",
      description=f"Badges offered by {requestor.mention} to {requestee.mention}",
      color=discord.Color.dark_purple()
    )
    offered_embed.set_image(url=f"attachment://{offered_image_id}.png")

    return offered_embed, offered_image

  async def _generate_requested_embed_and_image(self, active_trade):
    requestee = await self.bot.fetch_user(active_trade["requestee_id"])
    requestor = await self.bot.fetch_user(active_trade["requestor_id"])

    requested_badges = db_get_trade_requested_badges(active_trade)
    requested_badge_filenames = [f"{b['badge_name'].replace(' ', '_')}.png" for b in requested_badges]
    requested_image_id = f"{active_trade['id']}-requested"
    requested_image = generate_badge_trade_showcase(
      requested_badge_filenames,
      requested_image_id,
      f"Badge(s) Requested from {requestee.display_name}",
      f"{len(requested_badge_filenames)} Badges"
    )
    requested_embed = discord.Embed(
      title="Requested",
      description=f"Badges requested from {requestee.mention} by {requestor.mention}",
      color=discord.Color.dark_purple()
    )
    requested_embed.set_image(url=f"attachment://{requested_image_id}.png")

    return requested_embed, requested_image

  async def _generate_home_embed_and_image(self, active_trade):
    requestor = await self.bot.fetch_user(active_trade["requestor_id"])
    requestee = await self.bot.fetch_user(active_trade["requestee_id"])

    offered_badge_names, requested_badge_names = await self._get_offered_and_requested_badge_names(active_trade)

    home_embed = None
    home_image = None
    if active_trade["status"] == 'active':
      home_embed = discord.Embed(
        title="Trade Offered!",
        description=f"Get that, get that, gold pressed latinum!\n\n{requestor.mention} has offered a trade to {requestee.mention}!",
        color=discord.Color.dark_purple()
      )
      home_embed.add_field(
        name=f"Offered by {requestor.display_name}",
        value=offered_badge_names
      )
      home_embed.add_field(
        name=f"Requested from {requestee.display_name}",
        value=requested_badge_names
      )
      home_embed.set_footer(text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}")

      home_image = discord.File(fp="./images/trades/assets/trade_offer.png", filename="trade_offer.png")
      home_embed.set_image(url=f"attachment://trade_offer.png")
    elif active_trade["status"] == 'pending':
      home_embed = discord.Embed(
        title="Trade Pending...",
        description=f"Ready to send?\n\nThis your pending trade with {requestee.mention}.\n\nUse `/trade activate` to send the request if it looks good to go!",
        color=discord.Color(0x99aab5)
      )
      home_embed.add_field(
        name=f"Offered by {requestor.display_name}",
        value=offered_badge_names
      )
      home_embed.add_field(
        name=f"Requested from {requestee.display_name}",
        value=requested_badge_names
      )

      home_image = discord.File(fp="./images/trades/assets/trade_pending.png", filename="trade_pending.png")
      home_embed.set_image(url=f"attachment://trade_pending.png")

    return home_embed, home_image


  @trade.command(
    name="activate",
    description="Send your pending trade offer to the recipient and alert the channel"
  )
  async def activate(self, ctx):
    try:
      active_trade = await self.check_for_active_trade(ctx)
      if not active_trade:
        return

      requestor = await self.bot.fetch_user(active_trade["requestor_id"])
      requestee = await self.bot.fetch_user(active_trade["requestee_id"])

      if active_trade["status"] == 'active':
        await ctx.respond(embed=discord.Embed(
          title="Already Active",
          description=f"You already have an active request open with {requestee.mention}!\n\nYou can cancel this request with `/trade` cancel if you wish to start a new one!",
          color=discord.Color.blurple()
        ), ephemeral=True)
        return

      if not does_trade_contain_badges(active_trade):
        await ctx.respond(embed=discord.Embed(
          title="Invalid Trade",
          description="You must either `/trade request` or `/trade offer` to include at least one badge before sending a request.",
          color=discord.Color.red()
        ), ephemeral=True)
        return

      offered_badge_names, requested_badge_names = await self._get_offered_and_requested_badge_names(active_trade)

      view = SendConfirmView(self)
      confirmation_embed = discord.Embed(
        title="Trade Confirmation",
        description=f"You're about to send your trade request to {requestee.mention}.\n\nAre you sure?",
        color=discord.Color.blurple()
      ).add_field(
        name=f"Offered by {requestor.display_name}",
        value=offered_badge_names
      ).add_field(
        name=f"Requested from {requestee.display_name}",
        value=requested_badge_names
      )

      await ctx.respond(
        embed=confirmation_embed,
        view=view,
        ephemeral=True
      )
      await view.wait()
      if view.value:
        db_activate_trade(active_trade)

        logger.info(f"{Fore.CYAN}{requestor.display_name} has activated a trade with {requestee.display_name}{Style.RESET_ALL}")

        active_trade["status"] = "active"

        # Home Page
        home_embed, home_image = await self._generate_home_embed_and_image(active_trade)
        # Offered page
        offered_embed, offered_image = await self._generate_offered_embed_and_image(active_trade)
        # Requested Page
        requested_embed, requested_image = await self._generate_requested_embed_and_image(active_trade)

        home_message = await ctx.channel.send(embed=home_embed, file=home_image)
        await ctx.channel.send(embed=offered_embed, file=offered_image)
        await ctx.channel.send(embed=requested_embed, file=requested_image)

        # Give notice to Requestee
        user = get_user(requestee.id)
        if user["receive_notifications"]:
          try:
            requestee_embed = discord.Embed(
              title="Trade Offered",
              description=f"Hey there, wanted to let you know that {requestor.mention} has requested a trade from you on The USS Hood.\n\nUse `/trade reply` in the channel review and either accept or deny!\n\nYou can also see their offer at {home_message.jump_url}!",
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
            await requestee.send(embed=requestee_embed)
          except discord.Forbidden as e:
            logger.info(f"Unable to send trade cancelation message to {requestor.display_name}, they have their DMs closed.")
            pass


      else:
        await ctx.send_followup(embed=discord.Embed(
          title="Confirmation Canceled",
          description="No action taken.\n\nYou may continue to modify the pending trade with \n`/trade offer` and `/trade request`",
          color=discord.Color.dark_purple()
        ), ephemeral=True)
    except Exception as e:
      logger.info(traceback.format_exc())


  @trade.command(
    name="offer",
    description="Add/Remove Badges you've offered in your current Outgoing Trade"
  )
  @option(
    name="action",
    description="Adding or Removing from the trade?",
    required=True,
    choices=[
      discord.OptionChoice(
        name="Add to Offer",
        value="add"
      ),
      discord.OptionChoice(
        name="Remove from Offer",
        value="remove"
      )
    ]
  )
  @option(
    name="badge",
    description="The name of your Badge",
    required=True,
    autocomplete=autocomplete_requestor_badges
  )
  @commands.check(access_check)
  async def offer(self, ctx, action:str, badge:str):
    active_trade = await self.check_for_active_trade(ctx)
    if not active_trade:
      return

    requestee = await self.bot.fetch_user(active_trade["requestee_id"])
    requestee_badges = db_get_user_badge_names(active_trade["requestee_id"])
    requestee_badge_names = [b["badge_name"].replace(".png", "").replace("_", " ") for b in requestee_badges]

    requestor_badges = db_get_user_badge_names(active_trade["requestor_id"])
    requestor_badge_names = [b["badge_name"].replace(".png", "").replace("_", " ") for b in requestor_badges]
    if badge not in requestor_badge_names:
      await ctx.respond(embed=discord.Embed(
        title="You don't possess that badge",
        description=f"`{badge}` does not match any badges you possess.\n\nUse `/badges` to view your current badge collection!",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    badge_filename = f"{badge.replace(' ', '_')}.png"
    discord_image = discord.File(fp=f"./images/badges/{badge_filename}", filename=badge_filename)

    trade_badges = db_get_trade_offered_badges(active_trade)
    trade_badge_names = [b["badge_name"] for b in trade_badges]

    if badge in trade_badge_names:
      if action == 'add':
        await ctx.respond(embed=discord.Embed(
          title=f"{badge} already exists in offer.",
          description="No action taken.",
          color=discord.Color.red()
        ), ephemeral=True)
        return
      elif action == 'remove':
        db_remove_badge_from_trade_offer(active_trade, badge)
        logger.info(f"{Fore.CYAN}{ctx.author.display_name} has removed the badge `{badge}` from their pending trade offer to {requestee.display_name}{Style.RESET_ALL}")

        removal_embed = discord.Embed(
          title=f"{badge} removed from offer.",
          description=f"This badge is no longer part of your offer to {requestee.mention}",
          color=discord.Color.dark_gold()
        )
        removal_embed.set_image(url=f"attachment://{badge_filename}")
        await ctx.respond(embed=removal_embed, file=discord_image, ephemeral=True)
        return
    else:
      if action == 'add':
        if len(trade_badges) >= self.max_badges_per_trade:
          await ctx.respond(embed=discord.Embed(
            title=f"Unable to add {badge} to offer.",
            description=f"You're at the max number of badges allowed per trade ({self.max_badges_per_trade})!",
            color=discord.Color.red()
          ), ephemeral=True)
          return
        elif badge in requestee_badge_names:
          await ctx.respond(embed=discord.Embed(
            title=f"{requestee.display_name} already has {badge}",
            description=f"Please try a different badge!",
            color=discord.Color.red()
          ), ephemeral=True)
          return
        else:
          db_add_badge_to_trade_offer(active_trade, badge)
          logger.info(f"{Fore.CYAN}{ctx.author.display_name} has added the badge `{badge}` to their pending trade offer to {requestee.display_name}{Style.RESET_ALL}")

          addition_embed = discord.Embed(
            title=f"{badge} added to offer.",
            description=f"This badge has been added to your offer to {requestee.mention}",
            color=discord.Color.dark_green()
          )
          addition_embed.set_image(url=f"attachment://{badge_filename}")
          await ctx.respond(embed=addition_embed, file=discord_image, ephemeral=True)
          return
      elif action == 'remove':
        await ctx.respond(embed=discord.Embed(
          title=f"{badge} did not exist in offer.",
          description="No action taken",
          color=discord.Color.dark_gold()
        ), ephemeral=True)


  @trade.command(
    name="request",
    description="Add/Remove Badges you've requested in your current Outgoing Trade"
  )
  @option(
    name="action",
    description="Adding or Removing from the Trade?",
    required=True,
    choices=[
      discord.OptionChoice(
        name="Add to Request",
        value="add"
      ),
      discord.OptionChoice(
        name="Remove from Request",
        value="remove"
      )
    ]
  )
  @option(
    name="badge",
    description="The name of your badge you would like to add/remove from the request",
    required=True,
    autocomplete=autocomplete_requestee_badges
  )
  @commands.check(access_check)
  async def request(self, ctx, action:str, badge:str):
    active_trade = await self.check_for_active_trade(ctx)
    if not active_trade:
      return

    requestor_badges = db_get_user_badge_names(active_trade["requestor_id"])
    requestor_badge_names = [b["badge_name"].replace(".png", "").replace("_", " ") for b in requestor_badges]

    requestee = await self.bot.fetch_user(active_trade["requestee_id"])
    requestee_badges = db_get_user_badge_names(active_trade["requestee_id"])
    requestee_badge_names = [b["badge_name"].replace(".png", "").replace("_", " ") for b in requestee_badges]

    if badge not in requestee_badge_names:
      await ctx.respond(embed=discord.Embed(
        title=f"{requestee.display_name} does not possess that badge",
        description=f"`{badge}` does not match any badges they possess.\n\nYou can use the autocomplete in the query to find the badges they do have!",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    badge_filename = f"{badge.replace(' ', '_')}.png"
    discord_image = discord.File(fp=f"./images/badges/{badge_filename}", filename=badge_filename)

    trade_badges = db_get_trade_requested_badges(active_trade)
    trade_badge_names = [b["badge_name"] for b in trade_badges]

    if badge in trade_badge_names:
      if action == 'add':
        await ctx.respond(embed=discord.Embed(
          title=f"{badge} already exists in request.",
          description="No action taken.",
          color=discord.Color.red()
        ), ephemeral=True)
        return
      elif action == 'remove':
        db_remove_badge_from_trade_request(active_trade, badge)
        logger.info(f"{Fore.CYAN}{ctx.author.display_name} has removed the badge `{badge}` from their pending trade request from {requestee.display_name}{Style.RESET_ALL}")

        removal_embed = discord.Embed(
          title=f"{badge} removed from request.",
          description=f"This badge is no longer part of your request from {requestee.mention}",
          color=discord.Color.dark_gold()
        )
        removal_embed.set_image(url=f"attachment://{badge_filename}")
        await ctx.respond(embed=removal_embed, file=discord_image, ephemeral=True)
        return
    else:
      if action == 'add':
        if len(trade_badges) >= self.max_badges_per_trade:
          await ctx.respond(embed=discord.Embed(
            title=f"Unable to add {badge} to request.",
            description=f"You're at the max number of badges allowed per trade ({self.max_badges_per_trade})!",
            color=discord.Color.red()
          ), ephemeral=True)
          return
        elif badge in requestor_badge_names:
          await ctx.respond(embed=discord.Embed(
            title=f"You already have {badge}!",
            description=f"No need to request this one!",
            color=discord.Color.red()
          ), ephemeral=True)
          return
        else:
          db_add_badge_to_trade_request(active_trade, badge)
          logger.info(f"{Fore.CYAN}{ctx.author.display_name} has added the badge `{badge}` from their pending trade request from {requestee.display_name}{Style.RESET_ALL}")

          addition_embed = discord.Embed(
            title=f"{badge} added to request.",
            description=f"This badge has been added to your request from {requestee.mention}",
            color=discord.Color.dark_green()
          )
          addition_embed.set_image(url=f"attachment://{badge_filename}")
          await ctx.respond(embed=addition_embed, file=discord_image, ephemeral=True)
          return
      elif action == 'remove':
        await ctx.respond(f"**{badge}** did not exist in request. No action taken.", ephemeral=True)


  async def check_for_active_trade(self, ctx):
    active_trade = db_get_active_requestor_trade(ctx.author.id)

    # If we don't have an active trade for this user, go ahead and let them know
    if not active_trade:
      inactive_embed = discord.Embed(
        title="You don't have a pending or active trade open!",
        description="You can start a new trade with `/trade initiate`!",
        color=discord.Color.red()
      )
      await ctx.respond(embed=inactive_embed, ephemeral=True)

    return active_trade

  async def _get_offered_and_requested_badge_names(self, active_trade):
    offered_badges = db_get_trade_offered_badges(active_trade)
    offered_badge_names = "None"
    if offered_badges:
      offered_badge_names = "\n".join([b['badge_name'] for b in offered_badges])

    requested_badges = db_get_trade_requested_badges(active_trade)
    requested_badge_names = "None"
    if requested_badges:
      requested_badge_names = "\n".join([b['badge_name'] for b in requested_badges])

    return offered_badge_names, requested_badge_names



#  ____ ___   __  .__.__
# |    |   \_/  |_|__|  |   ______
# |    |   /\   __\  |  |  /  ___/
# |    |  /  |  | |  |  |__\___ \
# |______/   |__| |__|____/____  >
#                              \/
def does_trade_contain_badges(active_trade):
  offered_badges = db_get_trade_offered_badges(active_trade)
  requested_badges = db_get_trade_requested_badges(active_trade)

  if len(offered_badges) > 0 or len(requested_badges) > 0:
    return True
  else:
    return False

# ________                      .__
# \_____  \  __ __   ___________|__| ____   ______
#  /  / \  \|  |  \_/ __ \_  __ \  |/ __ \ /  ___/
# /   \_/.  \  |  /\  ___/|  | \/  \  ___/ \___ \
# \_____\ \_/____/  \___  >__|  |__|\___  >____  >
#        \__>           \/              \/     \/
def db_get_trade_requested_badges(active_trade):
  active_trade_id = active_trade["id"]

  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT b_i.badge_name
    FROM badge_info as b_i
      JOIN trade_requested AS t_r
      ON t_r.trade_id = %s AND t_r.badge_id = b_i.id
  '''
  vals = (active_trade_id,)
  query.execute(sql, vals)
  trades = query.fetchall()
  db.commit()
  query.close()
  db.close()
  return trades

def db_get_trade_offered_badges(active_trade):
  active_trade_id = active_trade["id"]

  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT b_i.badge_name
    FROM badge_info as b_i
      JOIN trade_offered AS t_o
      ON t_o.trade_id = %s AND t_o.badge_id = b_i.id
  '''
  vals = (active_trade_id,)
  query.execute(sql, vals)
  trades = query.fetchall()
  db.commit()
  query.close()
  db.close()
  return trades

def db_add_badge_to_trade_offer(active_trade, badge_name):
  active_trade_id = active_trade["id"]

  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    INSERT INTO trade_offered (trade_id, badge_id)
      VALUES (%s, (SELECT id FROM badge_info WHERE badge_name = %s))
  '''
  vals = (active_trade_id, badge_name)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()

def db_remove_badge_from_trade_offer(active_trade, badge_name):
  active_trade_id = active_trade["id"]

  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    DELETE FROM trade_offered
      WHERE trade_id = %s AND badge_id = (SELECT id FROM badge_info WHERE badge_name = %s)
  '''
  vals = (active_trade_id, badge_name)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()

def db_add_badge_to_trade_request(active_trade, badge_name):
  active_trade_id = active_trade["id"]

  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    INSERT INTO trade_requested (trade_id, badge_id)
      VALUES (%s, (SELECT id FROM badge_info WHERE badge_name = %s))
  '''
  vals = (active_trade_id, badge_name)
  query.execute(sql, vals)
  logger.info(">> Added badge to trade request.")
  db.commit()
  query.close()
  db.close()

def db_remove_badge_from_trade_request(active_trade, badge_name):
  active_trade_id = active_trade["id"]

  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    DELETE FROM trade_requested
      WHERE trade_id = %s AND badge_id = (SELECT id FROM badge_info WHERE badge_name = %s)
  '''
  vals = (active_trade_id, badge_name)
  query.execute(sql, vals)
  logger.info(">> Removed badge from trade request.")
  db.commit()
  query.close()
  db.close()

def db_get_user_badge_names(discord_id):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT badge_name FROM badges WHERE user_discord_id = %s"
  vals = (discord_id,)
  query.execute(sql, vals)
  badge_names = query.fetchall()
  db.commit()
  query.close()
  db.close()
  return badge_names

def db_get_active_requestee_trades(requestee_id):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT * FROM trades WHERE requestee_id = %s AND status = 'active'"
  vals = (requestee_id,)
  query.execute(sql, vals)
  trades = query.fetchall()
  db.commit()
  query.close()
  db.close()
  return trades

def db_get_active_requestor_trade(requestor_id):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT * FROM trades WHERE requestor_id = %s AND (status = 'active' OR status = 'pending') LIMIT 1"
  vals = (requestor_id,)
  query.execute(sql, vals)
  trade = query.fetchone()
  db.commit()
  query.close()
  db.close()
  return trade

def db_get_active_trade_between_requestor_and_requestee(requestor_id, requestee_id):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT * FROM trades WHERE requestor_id = %s AND requestee_id = %s AND status = 'active' LIMIT 1"
  vals = (requestor_id, requestee_id)
  query.execute(sql, vals)
  trade = query.fetchone()
  db.commit()
  query.close()
  db.close()
  return trade

def db_initiate_trade(requestor_id, requestee_id):
  db = getDB()
  query = db.cursor()
  sql = "INSERT INTO trades (requestor_id, requestee_id, status) VALUES (%s, %s, 'pending')"
  vals = (requestor_id, requestee_id)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()

def db_activate_trade(active_trade):
  active_trade_id = active_trade["id"]

  db = getDB()
  query = db.cursor()
  sql = "UPDATE trades SET status = 'active' WHERE id = %s"
  vals = (active_trade_id,)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()

def db_cancel_trade(trade):
  trade_id = trade['id']
  db = getDB()
  query = db.cursor()
  sql = "UPDATE trades SET status = 'canceled' WHERE id = %s"
  vals = (trade_id,)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()

def db_perform_badge_transfer(active_trade):
  trade_id = active_trade['id']
  requestor_id = active_trade['requestor_id']
  requestee_id = active_trade['requestee_id']
  db = getDB()
  query = db.cursor(dictionary=True)

  # Transfer Requested Badges to Requestor
  sql = '''
    INSERT INTO badges (user_discord_id, badge_name)
      SELECT t.requestor_id, b_i.badge_filename
        FROM trades as t
        JOIN badge_info as b_i
        JOIN trade_requested as t_r
          ON t.id = %s AND t_r.trade_id = t.id AND t_r.badge_id = b_i.id
  '''
  vals = (trade_id,)
  query.execute(sql, vals)

  # Delete Requested Badges from Requestee
  sql = '''
    DELETE b FROM badges b
      JOIN badge_info b_i ON b.badge_name = b_i.badge_filename
      JOIN trade_requested t_r ON t_r.badge_id = b_i.id
      JOIN trades t ON t_r.trade_id = t.id
        WHERE (t.id = %s AND t.requestee_id = %s AND b.user_discord_id = %s)
  '''
  vals = (trade_id, requestee_id, requestee_id)
  query.execute(sql, vals)

  # Transfer Offered Badges to Requestee
  sql = '''
    INSERT INTO badges (user_discord_id, badge_name)
      SELECT t.requestee_id, b_i.badge_filename
        FROM trades as t
        JOIN badge_info as b_i
        JOIN trade_offered as t_o
          ON t.id = %s AND t_o.trade_id = t.id AND t_o.badge_id = b_i.id
  '''
  vals = (trade_id,)
  query.execute(sql, vals)

  # Delete Offered Badges from Requestor
  sql = '''
    DELETE b FROM badges b
      JOIN badge_info b_i ON b.badge_name = b_i.badge_filename
      JOIN trade_offered t_o ON t_o.badge_id = b_i.id
      JOIN trades t ON t_o.trade_id = t.id
        WHERE (t.id = %s AND t.requestor_id = %s AND b.user_discord_id = %s)
  '''
  vals = (trade_id, requestor_id, requestor_id)
  query.execute(sql, vals)

  db.commit()
  query.close()
  db.close()

def db_complete_trade(active_trade):
  trade_id = active_trade['id']
  db = getDB()
  query = db.cursor()
  sql = "UPDATE trades SET status = 'complete' WHERE id = %s"
  vals = (trade_id,)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()

def db_decline_trade(active_trade):
  trade_id = active_trade['id']
  db = getDB()
  query = db.cursor()
  sql = "UPDATE trades SET status = 'declined' WHERE id = %s"
  vals = (trade_id,)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()

def db_get_related_badge_trades(active_trade):
  active_trade_id = active_trade["id"]
  requestee_id = active_trade["requestee_id"]
  requestor_id = active_trade["requestor_id"]

  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT * FROM trades
      WHERE status = 'active' OR status = 'pending'
      AND (requestee_id = %s OR requestor_id = %s OR requestee_id = %s OR requestor_id = %s)
      AND (id IN (
          SELECT trade_id FROM trade_requested
            WHERE badge_id IN (
              SELECT badge_id FROM trade_requested WHERE trade_id = %s
            ) OR badge_id IN (
              SELECT badge_id FROM trade_offered WHERE trade_id = %s
            )
        ) OR id IN (
          SELECT trade_id FROM trade_offered
            WHERE badge_id IN (
              SELECT badge_id FROM trade_offered WHERE trade_id = %s
            ) OR badge_id IN (
              SELECT badge_id FROM trade_requested WHERE trade_id = %s
            )
        )
      )
  '''
  vals = (
    requestee_id, requestee_id,
    requestor_id, requestor_id,
    active_trade_id, active_trade_id,
    active_trade_id, active_trade_id
  )
  query.execute(sql, vals)
  trades = query.fetchall()
  db.commit()
  query.close()
  db.close()
  return trades