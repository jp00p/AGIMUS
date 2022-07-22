from common import *
from utils.check_channel_access import access_check


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

      # Deny requests to users that do not have XP enabled
      requestee_details = get_user(requestee_id)
      if not requestee_details["xp_enabled"]:
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
        description="Your trade has been initiated with status: `pending`.\n\nFollow up with `/trade request` and `/trade offer` to fill out the trade details!\n\nOnce the details have been filled out, use `/trade send`!\n\nNote: You may only have one open trade request at a time!\nUse `/trade cancel` if you wish to dismiss the current trade.",
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
      active_trade = get_active_requestor_trade(ctx.author.id)

      # If we don't have an active trade for this user, go ahead and let them know
      if not active_trade:
        inactive_embed = discord.Embed(
          title="⁉️ You don't have an outgoing trade open!",
          description="Nothing to cancel. You can start a new trade with `/trade initiate`!",
          color=discord.Color.red()
        )
        await ctx.respond(embed=inactive_embed, ephemeral=True)
        return

      # Otherwise, cancel the trade and send confirmation
      cancel_trade(active_trade['id'])

      active_trade_requestee = await self.bot.fetch_user(active_trade["requestee_id"])
      confirmation_description = f"Your trade with {active_trade_requestee.mention} has been canceled!\n\n"
      if active_trade["active"]:
        confirmation_description += "**Reason:** {reason }\n\n"
      confirmation_description += "You may now begin a new trade request with `/trade initiate`"
      confirmation_embed = discord.Embed(
        title="❌ Trade Canceled!",
        description=confirmation_description,
        color=discord.Color.dark_purple()
      )
      if active_trade["active"]:
        confirmation_embed.set_footer(text="Because the trade was active, we've let them know you have canceled the request.")
      await ctx.respond(embed=confirmation_embed, ephemeral=True)

      # If the trade was active, alert the requestee that the trade has been canceled
      if active_trade["active"]:
        requestor = ctx.author
        notification_description = f"Heads up! {requestor.mention} has canceled their pending trade request with you."
        if reason:
          notification_description += f"\n\n**Reason:** {reason}"

        notification_embed = discord.Embed(
          title="❌ Trade Canceled!",
          description=notification_description,
          color=discord.Color.dark_purple()
        )
        await active_trade_requestee.send(embed=notification_embed)
    except Exception as e:
      logger.info(traceback.format_exc())


def get_active_requestee_trades(requestee_id):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT * FROM trades WHERE requestee_id = %s AND active = 1"
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
  sql = "SELECT * FROM trades WHERE requestor_id = %s AND (active = 1 OR pending = 1) LIMIT 1"
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
  sql = "INSERT INTO trades (requestor_id, requestee_id, pending) VALUES (%s, %s, %s)"
  vals = (requestor_id, requestee_id, 1)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()

def cancel_trade(trade_id):
  db = getDB()
  query = db.cursor()
  sql = "UPDATE trades SET pending = 0, active = 0, completed = 0, canceled = 1 WHERE id = %s"
  vals = (trade_id,)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()