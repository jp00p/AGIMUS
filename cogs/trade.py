from distutils.command.build_scripts import build_scripts
from common import *
from utils.badge_utils import generate_badge_trade_showcase
from utils.check_channel_access import access_check


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

  @discord.ui.button(label="   Cancel   ", style=discord.ButtonStyle.grey)
  async def cancel_callback(self, button:discord.ui.Button, interaction:discord.Interaction):
    self.disable_all_items()
    await interaction.response.edit_message(view=self)
    self.value = False
    self.stop()

  @discord.ui.button(label="   Confirm   ", style=discord.ButtonStyle.green)
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
      # Disable View Once Selected
      view = self.view
      view.disable_all_items()
      await interaction.response.edit_message(view=view)
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

class RejectButton(discord.ui.Button):
  def __init__(self, cog, active_trade):
    self.cog = cog
    self.active_trade = active_trade
    super().__init__(
      label="     Reject     ",
      style=discord.ButtonStyle.red,
      row=2
    )

  async def callback(self, interaction: discord.Interaction):
    view = self.view
    view.disable_all_items()
    await interaction.response.edit_message(view=view)
    await self.cog._reject_trade_callback(interaction, self.active_trade)

class AcceptRejectView(discord.ui.View):
  def __init__(self, cog, active_trade):
    super().__init__()
    self.add_item(RejectButton(cog, active_trade))
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
    # TODO: Put this somewhere better
    self.rules_of_acquisition = [
      "No. 1: Once you have their money, you never give it back.",
      "No. 3: Never spend more for an acquisition than you have to.",
      "No. 6: Never allow family to stand in the way of opportunity.",
      "No. 7: Keep your ears open.",
      "No. 9: Opportunity plus instinct equals profit.",
      "No. 10: Greed is eternal.",
      "No. 16: A deal is a deal.",
      "No. 17: A contract is a contract is a contract… but only between Ferengi.",
      "No. 18: A Ferengi without profit is no Ferengi at all.",
      "No. 21: Never place friendship above profit.",
      "No. 22: A wise man can hear profit in the wind.",
      "No. 23: Nothing is more important than your health… except for your money.",
      "No. 31: Never make fun of a Ferengi's mother.",
      "No. 33: It never hurts to suck up to the boss.",
      "No. 34: War is good for business.",
      "No. 35: Peace is good for business.",
      "No. 45: Expand or die.",
      "No. 47: Don't trust a man wearing a better suit than your own.",
      "No. 48: The bigger the smile, the sharper the knife.",
      "No. 57: Good customers are as rare as latinum. Treasure them.",
      "No. 59: Free advice is seldom cheap.",
      "No. 62: The riskier the road, the greater the profit.",
      "No. 74: Knowledge equals profit.",
      "No. 75: Home is where the heart is, but the stars are made of latinum.",
      "No. 76: Every once in a while, declare peace. It confuses the hell out of your enemies.",
      "No. 98: Every man has his price.",
      "No. 102: Nature decays, but latinum lasts forever.",
      "No. 109: Dignity and an empty sack is worth the sack.",
      "No. 111: Treat people in your debt like family… exploit them.",
      "No. 125: You can't make a deal if you're dead.",
      "No. 168: Whisper your way to success.",
      "No. 190: Hear all, trust nothing.",
      "No. 194: It's always good business to know about new customers before they walk in your door.",
      "No. 203: New customers are like razor-toothed gree-worms. They can be succulent, but sometimes they bite back.",
      "No. 208: Sometimes the only thing more dangerous than a question is an answer.",
      "No. 214: Never begin a business negotiation on an empty stomach.",
      "No. 217: You can't free a fish from water.",
      "No. 239: Never be afraid to mislabel a product.",
      "No. 263: Never allow doubt to tarnish your lust for latinum.",
      "No. 285: No good deed ever goes unpunished."
    ]


  # NOTE:
  # EDGECASES:
  # - Need to make sure if trade is requested but the requestee or requestor doesn't have the pins anymore, it's rejected and canceled
  # - On trade completed, cancel any existing trades for those users that may have included those pins that were transferred

  trade = discord.SlashCommandGroup("trade", "Commands for trading badges")


  # INCOMING TRADE
  @trade.command(
    name="accept",
    description="View and Accept/Reject incoming trades from other users"
  )
  @commands.check(access_check)
  async def accept(self, ctx:discord.ApplicationContext):
    incoming_trades = db_get_active_requestee_trades(ctx.user.id)

    if not incoming_trades:
      await ctx.respond(embed=discord.Embed(
        title="No Incoming Trade Requests",
        description="No one has any active trades requested from you. Get out there are start hustlin!",
        color=discord.Color.blurple()
      ), ephemeral=True)
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
      ),
      view=view,
      ephemeral=True
    )

  async def _send_trade_interface(self, interaction, requestor_id):
    requestee_id = interaction.user.id
    active_trade = db_get_active_trade_between_requestor_and_requestee(requestor_id, requestee_id)

    trade_pages = await self._generate_trade_pages(active_trade)
    view = AcceptRejectView(self, active_trade)
    paginator = pages.Paginator(
      pages=trade_pages,
      use_default_buttons=False,
      custom_buttons=self.trade_buttons,
      custom_view=view,
      loop_pages=True
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

    offered_badges = db_get_trade_offered_badges(active_trade)
    offered_badges_string = "None"
    if offered_badges:
      offered_badges_string = "\n".join([b['badge_name'] for b in offered_badges])
    
    requested_badges = db_get_trade_requested_badges(active_trade)
    requested_badges_string = "None"
    if offered_badges:
      requested_badges_string = "\n".join([b['badge_name'] for b in requested_badges])

    success_embed = discord.Embed(
      title="Successful Trade!",
      description=f"{requestor.mention} and {requestee.mention} came to an agreement!\n\nBadges transferred successfully!",
      color=discord.Color.dark_purple()
    )
    success_embed.add_field(
      name=f"{requestor.display_name} received",
      value=requested_badges_string
    )
    success_embed.add_field(
      name=f"{requestee.display_name} received",
      value=offered_badges_string
    )
    success_image = discord.File(fp="./images/trades/assets/trade_success.png", filename="trade_success.png")
    success_embed.set_image(url=f"attachment://trade_success.png")
    success_embed.set_footer(text=f"Ferengi Rule of Acquisition {random.choice(self.rules_of_acquisition)}")

    channel = interaction.channel
    await channel.send(embed=success_embed, file=success_image)

  async def _cancel_invalid_related_trades(self, active_trade):
    # These are all the trades that involve either the requestee or requestor
    # and the badges that are involved with the the trade we're about to cancel
    related_trades = db_get_related_badge_trades(active_trade)

    # Filter out the current trade itself, then cancel the others
    trades_to_cancel = [t for t in related_trades if t["id"] != active_trade["id"]]

    # Iterate through to cancel, and then 
    for trade in trades_to_cancel:
      db_cancel_trade(trade)
      requestee = await self.bot.fetch_user(trade['requestee_id'])
      requestor = await self.bot.fetch_user(trade['requestor_id'])

      offered_badges = db_get_trade_offered_badges(trade)
      offered_badges_string = "None"
      if offered_badges:
        offered_badges_string = "\n".join([b["badge_name"] for b in offered_badges])

      requested_badges = db_get_trade_requested_badges(trade)
      requested_badges_string = "None"
      if requested_badges:
        requested_badges_string = "\n".join([b["badge_name"] for b in requested_badges])

      # Give notice to Requestee
      await requestee.send(embed=discord.Embed(
          title="Trade Canceled",
          description=f"Just a heads up! Your USS Hood Badge Trade requested from {requestor.mention} was canceled because one or more of the badges involved were traded to another user.",
          color=discord.Color.purple()
        ).set_footer(
          text="Thank you and have a nice day!"
        ).add_field(
          name=f"Offered by {requestor.display_name}", value=offered_badges_string
        ).add_field(
          name=f"Requested from {requestee.display_name}", value=requested_badges_string
        )
      )

      # Give notice to Requestor
      await requestor.send(embed=discord.Embed(
          title="Trade Canceled",
          description=f"Just a heads up! Your USS Hood Badge Trade requested by {requestee.mention} was canceled because one or more of the badges involved were traded to another user.",
          color=discord.Color.purple()
        ).set_footer(
          text="Thank you and have a nice day!"
        ).add_field(
          name=f"Offered by {requestor.display_name}", value=offered_badges_string
        ).add_field(
          name=f"Requested from {requestee.display_name}", value=requested_badges_string
        )
      )

  async def _reject_trade_callback(self, interaction, active_trade):
    db_reject_trade(active_trade)
    await interaction.response.send_message("Trade rejected", ephemeral=True)


  # OUTGOING TRADE!
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


      # Deny the trade request if the requestee already has 3 active trades pending
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

      # Confirmation initiation with the requestor
      confirmation_embed = discord.Embed(
        title="Trade Initiated!",
        description="Your trade has been initiated with status: `pending`.\n\nFollow up with `/trade request` and `/trade offer` to fill out the trade details!\n\nOnce you have added the badges you'd like to offer and request,\nuse `/trade activate` to send the trade to the user!\n\nNote: You may only have one open trade request at a time!\nUse `/trade cancel` if you wish to dismiss the current trade.",
        color=discord.Color.blurple()
      ).add_field(
        name="Requestor",
        value=f"{ctx.author.mention}"
      ).add_field(
        name="Requestee",
        value=f"{requestee.mention}"
      )
      confirmation_embed.set_footer(text="Happy trading!")
      await ctx.respond(embed=confirmation_embed, ephemeral=True)

    except Exception as e:
      logger.info(traceback.format_exc())


  @trade.command(
    name="cancel",
    description="Cancel your currently active or pending trade"
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

      active_trade_requestee = await self.bot.fetch_user(active_trade["requestee_id"])
      confirmation_description = f"Your trade with {active_trade_requestee.mention} has been canceled!\n\n"
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

      # If the trade was active, alert the requestee that the trade has been canceled
      # TODO: Uncomment this when ready to start pinging users for testing
      # if active_trade["status"] == 'active':
        # requestor = ctx.author
        # notification_description = f"Heads up! {requestor.mention} has canceled their pending trade request with you."
        # if reason:
        #   notification_description += f"\n\n**Reason:** {reason}"

        # notification_embed = discord.Embed(
        #   title="Trade Canceled!",
        #   description=notification_description,
        #   color=discord.Color.dark_purple()
        # )
        # await active_trade_requestee.send(embed=notification_embed)
    except Exception as e:
      logger.info(traceback.format_exc())


  @trade.command(
    name="status",
    description="Check the current status of your Outgoing Trade"
  )
  @commands.check(access_check)
  async def status(self, ctx):
    active_trade = await self.check_for_active_trade(ctx)
    if not active_trade:
      return

    await ctx.defer(ephemeral=True)

    trade_pages = await self._generate_trade_pages(active_trade)
    paginator = pages.Paginator(
      pages=trade_pages,
      use_default_buttons=False,
      custom_buttons=self.trade_buttons,
      loop_pages=True
    )

    await paginator.respond(ctx.interaction, ephemeral=True)

  async def _generate_trade_pages(self, active_trade):
    requestor = await self.bot.fetch_user(active_trade["requestor_id"])
    requestee = await self.bot.fetch_user(active_trade["requestee_id"])

    # Offered Page
    offered_badges = db_get_trade_offered_badges(active_trade)
    offered_badges_string = "None"
    if offered_badges:
      offered_badges_string = "\n".join([b['badge_name'] for b in offered_badges])
    offered_badge_filenames = [f"{b['badge_name'].replace(' ', '_')}.png" for b in offered_badges]
    offered_image_id = f"{active_trade['id']}-offered"
    offered_image = generate_badge_trade_showcase(
      offered_badge_filenames,
      offered_image_id,
      f"Badges Offered by {requestor.display_name}",
      f"{len(offered_badge_filenames)} Badges"
    )
    offered_embed = discord.Embed(
      title="Offered",
      description=f"Badges offered by {requestor.mention}",
      color=discord.Color.dark_purple()
    )
    offered_embed.set_image(url=f"attachment://{offered_image_id}.png")

    # Requested Page
    requested_badges = db_get_trade_requested_badges(active_trade)
    requested_badges_string = "None"
    if requested_badges:
      requested_badges_string = "\n".join([b['badge_name'] for b in requested_badges])
    requested_badge_filenames = [f"{b['badge_name'].replace(' ', '_')}.png" for b in requested_badges]
    requested_image_id = f"{active_trade['id']}-requested"
    requested_image = generate_badge_trade_showcase(
      requested_badge_filenames,
      requested_image_id,
      f"Badges Requested from {requestee.display_name}",
      f"{len(requested_badge_filenames)} Badges"
    )
    requested_embed = discord.Embed(
      title="Requested",
      description=f"Badges requested from {requestee.mention}",
      color=discord.Color.dark_purple()
    )
    requested_embed.set_image(url=f"attachment://{requested_image_id}.png")

    # Home Page
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
        value=offered_badges_string
      )
      home_embed.add_field(
        name=f"Requested from {requestee.display_name}",
        value=requested_badges_string
      )

      home_embed.set_footer(text="Use the buttons below to browse!")
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
        value=offered_badges_string
      )
      home_embed.add_field(
        name=f"Requested from {requestee.display_name}",
        value=requested_badges_string
      )

      home_embed.set_footer(text="Use the buttons below to browse!")
      home_image = discord.File(fp="./images/trades/assets/trade_pending.png", filename="trade_pending.png")
      home_embed.set_image(url=f"attachment://trade_pending.png")

    # PAGINATOR
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

  @trade.command(
    name="activate",
    description="Send your current Trade Offer to the recipient and channel"
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

      offered_badges = db_get_trade_offered_badges(active_trade)
      offered_badges_names = "None"
      if offered_badges:
        offered_badges_names = "\n".join([b['badge_name'] for b in offered_badges])

      requested_badges = db_get_trade_requested_badges(active_trade)
      requested_badges_names = "None"
      if requested_badges:
        requested_badges_names = "\n".join([b['badge_name'] for b in requested_badges])

      view = SendConfirmView(self)
      confirmation_embed = discord.Embed(
        title="Trade Confirmation",
        description=f"You're about to send your trade request to {requestee.mention}.\n\nAre you sure?",
        color=discord.Color.blurple()
      ).add_field(
        name=f"Offered by {requestor.display_name}",
        value=offered_badges_names
      ).add_field(
        name=f"Requested from {requestee.display_name}",
        value=requested_badges_names
      )

      confirmation = await ctx.respond(
        embed=confirmation_embed,
        view=view,
        ephemeral=True
      )
      await view.wait()
      if view.value:
        db_activate_trade(active_trade)
        active_trade["status"] = "active"

        trade_pages = await self._generate_trade_pages(active_trade)
        trade_buttons = self.trade_buttons
        paginator = pages.Paginator(
          pages=trade_pages,
          use_default_buttons=False,
          custom_buttons=trade_buttons,
          loop_pages=True
        )

        await paginator.respond(confirmation, ephemeral=False)
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
        title="⁉️ You don't have a pending or active trade open!",
        description="You can start a new trade with `/trade initiate`!",
        color=discord.Color.red()
      )
      await ctx.respond(embed=inactive_embed, ephemeral=True)

    return active_trade

# Check helpers
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

def db_reject_trade(active_trade):
  trade_id = active_trade['id']
  db = getDB()
  query = db.cursor()
  sql = "UPDATE trades SET status = 'rejected' WHERE id = %s"
  vals = (trade_id,)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()

def db_get_related_badge_trades(active_trade):
  active_trade_id = active_trade["id"]
  requestor_id = active_trade["requestor_id"]
  requestee_id = active_trade["requestee_id"]

  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT * FROM trades
      WHERE (status = 'active' OR status = 'pending')
      AND (
        (requestee_id = %s OR requestor_id = %s)
        OR
        (requestee_id = %s OR requestor_id = %s)
      )
      AND (
        id IN (
          SELECT trade_id FROM trade_requested
            WHERE badge_id IN (
              SELECT badge_id FROM trade_requested WHERE trade_id = %s
            )
        ) OR id IN (
          SELECT trade_id FROM trade_offered
            WHERE badge_id IN (
              SELECT badge_id FROM trade_offered WHERE trade_id = %s
            )
        )
      )
  '''
  vals = (
    requestor_id, requestor_id,
    requestee_id, requestee_id,
    active_trade_id, active_trade_id
  )
  query.execute(sql, vals)
  trades = query.fetchall()
  db.commit()
  query.close()
  db.close()
  return trades