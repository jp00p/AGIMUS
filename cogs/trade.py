from common import *
from utils.badge_utils import generate_badge_trade_showcase
from utils.check_channel_access import access_check


#   ___ ___         .__                              
#  /   |   \   ____ |  | ______   ___________  ______
# /    ~    \_/ __ \|  | \____ \_/ __ \_  __ \/  ___/
# \    Y    /\  ___/|  |_|  |_> >  ___/|  | \/\___ \ 
#  \___|_  /  \___  >____/   __/ \___  >__|  /____  >
#        \/       \/     |__|        \/           \/ 
async def requestor_badges(ctx:discord.AutocompleteContext):
  requestor_badges = get_user_badge_names(ctx.interaction.user.id)
  autocomplete_results = []
  for badge in requestor_badges:
    badge_name = badge["badge_name"].replace(".png", "").replace("_", " ")
    autocomplete_results.append(badge_name)
  return autocomplete_results

async def requestee_badges(ctx:discord.AutocompleteContext):
  active_trade = get_active_requestor_trade(ctx.interaction.user.id)
  requestee_badges = get_user_badge_names(active_trade['requestee_id'])
  autocomplete_results = []
  for badge in requestee_badges:
    badge_name = badge["badge_name"].replace(".png", "").replace("_", " ")
    autocomplete_results.append(badge_name)
  return autocomplete_results


# Define a simple View that gives us a confirmation menu.
class SendConfirm(discord.ui.View):
  def __init__(self, cog):
    super().__init__()
    self.value = None

  @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
  async def cancel_callback(self, button:discord.ui.Button, interaction:discord.Interaction):
    self.disable_all_items()
    await interaction.response.edit_message(view=self)
    self.value = False
    self.stop()

  @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
  async def confirm_callback(self, button:discord.ui.Button, interaction:discord.Interaction):
    self.disable_all_items()
    await interaction.response.edit_message(view=self)
    await interaction.followup.send(embed=discord.Embed(
      title="Trade Sent!",
      description="Let's see if they accept!",
      color=discord.Color.green()
    ), ephemeral=True)
    self.value = True
    self.stop()



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

  # NOTE:
  # EDGECASES:
  # - Need to make sure if trade is requested but the requestee or requestor doesn't have the pins anymore, it's rejected and canceled
  # - On trade completed, cancel any existing trades for those users that may have included those pins that were transferred

  trade = discord.SlashCommandGroup("trade", "Commands for trading badges")

  @trade.command(
    name="initiate",
    description="Initiate a trade with a specified user (only one trade active at a time)"
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
          title="🚫 This user is not participating.",
          description=f"Sorry, {requestee.mention} has opted out of the XP system and is not available for trading.",
          color=discord.Color.red()
        )
        await ctx.respond(embed=opted_out_embed, ephemeral=True)
        return


      # Deny the trade request if there's an existing trade in progress by the requestor
      active_trade = get_active_requestor_trade(requestor_id)
      if active_trade:
        active_trade_requestee = await self.bot.fetch_user(active_trade['requestee_id'])
        already_active_embed = discord.Embed(
          title="🚫 You already have an active trade!",
          description=f"You have a outgoing trade open with {active_trade_requestee.mention}.\n\nUse `/trade status` to view this current trade.\nUse `/trade cancel` to close the current trade if desired!\n\nThis must be resolved before you can open another request.",
          color=discord.Color.red()
        )
        already_active_embed.set_footer(text="You may want to check on this trade to see if they have had a chance to review your request!")
        await ctx.respond(embed=already_active_embed, ephemeral=True)
        return


      # Deny the trade request if the requestee already has 3 active trades pending
      requestee_trades = get_active_requestee_trades(requestee_id)
      if len(requestee_trades) >= self.max_trades:
        max_requestee_trades_embed = discord.Embed(
          title=f"🚫 {requestee.display_name} has too many pending trades!",
          description=f"Sorry, the person you've requested a trade from already has the maximum number of trade requests pending ({self.max_trades}).",
          color=discord.Color.red()
        )
        await ctx.respond(embed=max_requestee_trades_embed, ephemeral=True)
        return

      # If not denied, go ahead and initiate the new trade!
      initiate_trade(requestor_id, requestee_id)

      # Send confirmation to the requestor
      confirmation_embed = discord.Embed(
        title="🔀 Trade Initiated!",
        description="Your trade has been initiated with status: `pending`.\n\nFollow up with `/trade request` and `/trade offer` to fill out the trade details!\n\nOnce you have added the badges you'd like to offer and request, use `/trade send`!\n\nNote: You may only have one open trade request at a time!\nUse `/trade cancel` if you wish to dismiss the current trade.",
        color=discord.Color.blurple()
      )
      confirmation_embed.add_field(
        name="Requestor",
        value=f"{ctx.author.mention}"
      )
      confirmation_embed.add_field(
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
      cancel_trade(active_trade['id'])

      active_trade_requestee = await self.bot.fetch_user(active_trade["requestee_id"])
      confirmation_description = f"Your trade with {active_trade_requestee.mention} has been canceled!\n\n"
      if active_trade["status"] == 'active' and reason:
        confirmation_description += f"**Reason:** {reason}\n\n"
      confirmation_description += "You may now begin a new trade request with `/trade initiate`"
      confirmation_embed = discord.Embed(
        title="❌ Trade Canceled!",
        description=confirmation_description,
        color=discord.Color.dark_purple()
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
        #   title="❌ Trade Canceled!",
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

    await ctx.defer(ephemeral=False)

    trade_pages = await self._generate_trade_pages(active_trade)

    trade_buttons = [
      pages.PaginatorButton("prev", label="    ⬅     ", style=discord.ButtonStyle.primary, row=1),
      pages.PaginatorButton(
        "page_indicator", style=discord.ButtonStyle.gray, disabled=True, row=1
      ),
      pages.PaginatorButton("next", label="     ➡    ", style=discord.ButtonStyle.primary, row=1),
    ]
    paginator = pages.Paginator(
      pages=trade_pages,
      use_default_buttons=False,
      custom_buttons=trade_buttons,
      loop_pages=True
    )

    await paginator.respond(ctx.interaction, ephemeral=False)

  async def _generate_trade_pages(self, active_trade):
    requestor = await self.bot.fetch_user(active_trade["requestor_id"])
    requestee = await self.bot.fetch_user(active_trade["requestee_id"])

    # Offered Page
    offered_badges = get_trade_offered_badges(active_trade)
    offered_badge_filenames = [f"{b['badge_name'].replace(' ', '_')}.png" for b in offered_badges]
    offered_image_id = f"{active_trade['id']}-offered"
    offered_image = generate_badge_trade_showcase(
      offered_badge_filenames,
      offered_image_id,
      "Badges Offered",
      f"{len(offered_badge_filenames)} Badges"
    )
    offered_embed = discord.Embed(
      title="Offered",
      description=f"Badges offered by {requestor.mention}"
    )
    offered_embed.set_image(url=f"attachment://{offered_image_id}.png")

    # Requested Page
    requested_badges = get_trade_requested_badges(active_trade)
    requested_badge_filenames = [f"{b['badge_name'].replace(' ', '_')}.png" for b in requested_badges]
    requested_image_id = f"{active_trade['id']}-requested"
    requested_image = generate_badge_trade_showcase(
      requested_badge_filenames,
      requested_image_id,
      "Badges Requested",
      f"{len(requested_badge_filenames)} Badges"
    )
    requested_embed = discord.Embed(
      title="Requested",
      description=f"Badges requested from {requestee.mention}"
    )
    requested_embed.set_image(url=f"attachment://{requested_image_id}.png")

    # Home Page
    home_embed = discord.Embed(
      title="Trade Details",
      description=f"Wheelin and Dealin! {requestor.mention} has offered a trade to {requestee.mention}!"
    )
    home_embed.set_footer(text="Use the buttons below to browse!")
    home_image = discord.File(fp="./images/trades/assets/trade_offer.png", filename="trade_offer.png")
    home_embed.set_image(url=f"attachment://trade_offer.png")


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

  async def get_trade_status_embed(self, title, active_trade):
    # NOTE: Do these with sexy list comprehensions later
    offered_badges = get_trade_offered_badges(active_trade)
    offered_badge_names = []
    offered_badges_string = "None"
    if len(offered_badges) > 0:
      offered_badges_string = ""
    for o in offered_badges:
      badge_name = o["badge_name"]
      offered_badge_names.append(badge_name)
      offered_badges_string += f"{badge_name}\n"

    requested_badges = get_trade_requested_badges(active_trade)
    requested_badge_names = []
    requested_badges_string = "None"
    if len(requested_badges) > 0:
      requested_badges_string = ""
    for r in requested_badges:
      badge_name = r["badge_name"]
      requested_badge_names.append(r["badge_name"])
      requested_badges_string += f"{badge_name}\n"

    requestor = await self.bot.fetch_user(active_trade["requestor_id"])
    requestee = await self.bot.fetch_user(active_trade['requestee_id'])

    status_embed = discord.Embed(
      title=title,
      description=f"Status: `{active_trade['status'].title()}`",
      color=discord.Color.blurple()
    )
    status_embed.add_field(
      name="Offered By",
      value=requestor.mention,
      inline=False
    )
    status_embed.add_field(
      name="Requested From",
      value=requestee.mention,
      inline=False
    )
    status_embed.add_field(
      name="Offered Badges",
      value=offered_badges_string
    )
    status_embed.add_field(
      name="Requested Badges",
      value=requested_badges_string
    )
    status_embed.set_footer(text="Redesign of this information is pending!")

    return status_embed


  @trade.command(
    name="send",
    description="Send your current Trade Offer to the recipient and channel"
  )
  async def send(self, ctx):
    active_trade = await self.check_for_active_trade(ctx)
    if not active_trade:
      return

    if not does_trade_contain_badges(active_trade):
      await ctx.respond(embed=discord.Embed(
        title="Invalid Trade",
        description="You must either request or offer at least one badge before sending request.",
        color=discord.Color.red()
      ), ephemeral=True)
      return
    
    requestee = await self.bot.fetch_user(active_trade["requestee_id"])

    view = SendConfirm(self)
    await ctx.respond(
      embed=discord.Embed(
        title="Please confirm this trade.",
        description=f"You're about to send your trade request to {requestee.mention}. Are you sure?",
        color=discord.Color.blurple()
      ),
      view=view,
      ephemeral=True
    )
    await view.wait()
    if view.value:
      activate_trade(active_trade)
      active_trade["status"] = "active"
      status_embed = await self.get_trade_status_embed("🏛️ New Trade Request!", active_trade)
      await ctx.channel.send(embed=status_embed)
    else:
      await ctx.send_followup(embed=discord.Embed(
        title="Canceled",
        description="No action taken. You may continue to modify the pending trade with `/trade offer` and `/trade request`",
        color=discord.Color.red()
      ), ephemeral=True)

  @trade.command(
    name="offer",
    description="Add/Remove Badges from your current Trade Offer"
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
    autocomplete=discord.utils.basic_autocomplete(requestor_badges)
  )
  @commands.check(access_check)
  async def offer(self, ctx, action:str, badge:str):
    active_trade = await self.check_for_active_trade(ctx)
    if not active_trade:
      return

    trade_badges = get_trade_offered_badges(active_trade)

    trade_badge_names = []
    for b in trade_badges:
      trade_badge_names.append(b["badge_name"])

    if badge in trade_badge_names:
      if action == 'add':
        await ctx.respond(f"{badge} already exists in offer. No action taken.", ephemeral=True)
        return
      elif action == 'remove':
        remove_badge_from_trade_offer(active_trade, badge)
        await ctx.respond(f"{badge} removed from offer.", ephemeral=True)
        return
    else:
      if action == 'add':
        if len(trade_badges) >= 5:
          await ctx.respond(f"Unable to add {badge} to offer. You're at the max number of badges allowed per trade (5)!")
          return
        else:
          add_badge_to_trade_offer(active_trade, badge)
          await ctx.respond(f"{badge} added to offer.", ephemeral=True)
          return
      elif action == 'remove':
        await ctx.respond(f"{badge} did not exist in offer. No action taken.", ephemeral=True)


  @trade.command(
    name="request",
    description="Add/Remove Badges from your current Trade Request"
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
    autocomplete=discord.utils.basic_autocomplete(requestee_badges)
  )
  @commands.check(access_check)
  async def request(self, ctx, action:str, badge:str):
    active_trade = await self.check_for_active_trade(ctx)
    if not active_trade:
      return

    trade_badges = get_trade_requested_badges(active_trade)

    trade_badge_names = []
    for b in trade_badges:
      trade_badge_names.append(b["badge_name"])

    if badge in trade_badge_names:
      if action == 'add':
        await ctx.respond(f"{badge} already exists in request. No action taken.", ephemeral=True)
        return
      elif action == 'remove':
        remove_badge_from_trade_request(active_trade, badge)
        await ctx.respond(f"{badge} removed from request.", ephemeral=True)
        return
    else:
      if action == 'add':
        if len(trade_badges) >= 5:
          await ctx.respond(f"Unable to add {badge} to request. You're at the max number of badges allowed per trade (5)!")
          return
        else:
          add_badge_to_trade_request(active_trade, badge)
          await ctx.respond(f"{badge} added to request.", ephemeral=True)
          return
      elif action == 'remove':
        await ctx.respond(f"{badge} did not exist in request. No action taken.", ephemeral=True)


  async def check_for_active_trade(self, ctx):
    active_trade = get_active_requestor_trade(ctx.author.id)

    # If we don't have an active trade for this user, go ahead and let them know
    if not active_trade:
      inactive_embed = discord.Embed(
        title="⁉️ You don't have a pending trade open!",
        description="You can start a new trade with `/trade initiate`!",
        color=discord.Color.red()
      )
      await ctx.respond(embed=inactive_embed, ephemeral=True)

    return active_trade




# Check helpers
def does_trade_contain_badges(active_trade):
  offered_badges = get_trade_offered_badges(active_trade)
  requested_badges = get_trade_requested_badges(active_trade)

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
def get_trade_requested_badges(active_trade):
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

def get_trade_offered_badges(active_trade):
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

def add_badge_to_trade_offer(active_trade, badge_name):
  active_trade_id = active_trade["id"]

  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    INSERT INTO trade_offered (trade_id, badge_id)
      VALUES (%s, (SELECT id FROM badge_info WHERE badge_name = %s))
  '''
  vals = (active_trade_id, badge_name)
  query.execute(sql, vals)
  logger.info(">> Added badge to trade offer.")
  db.commit()
  query.close()
  db.close()

def remove_badge_from_trade_offer(active_trade, badge_name):
  active_trade_id = active_trade["id"]

  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    DELETE FROM trade_offered
      WHERE trade_id = %s AND badge_id = (SELECT id FROM badge_info WHERE badge_name = %s)
  '''
  vals = (active_trade_id, badge_name)
  query.execute(sql, vals)
  logger.info(">> Removed badge from trade offer.")
  db.commit()
  query.close()
  db.close()

def add_badge_to_trade_request(active_trade, badge_name):
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

def remove_badge_from_trade_request(active_trade, badge_name):
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

def get_user_badge_names(discord_id):
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

def get_active_requestee_trades(requestee_id):
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

def get_active_requestor_trade(requestor_id):
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

def initiate_trade(requestor_id, requestee_id):
  db = getDB()
  query = db.cursor()
  sql = "INSERT INTO trades (requestor_id, requestee_id, status) VALUES (%s, %s, 'pending')"
  vals = (requestor_id, requestee_id)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()

def activate_trade(active_trade):
  active_trade_id = active_trade["id"]

  db = getDB()
  query = db.cursor()
  sql = "UPDATE trades SET status = 'active' WHERE id = %s"
  vals = (active_trade_id,)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()

def cancel_trade(trade_id):
  db = getDB()
  query = db.cursor()
  sql = "UPDATE trades SET status = 'canceled' WHERE id = %s"
  vals = (trade_id,)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()