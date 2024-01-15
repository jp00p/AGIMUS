from common import *
from utils.badge_utils import *
from utils.check_channel_access import access_check

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
async def risk_autocomplete(ctx:discord.AutocompleteContext):
  first_badge = ctx.options["first_badge"]
  second_badge = ctx.options["second_badge"]
  third_badge = ctx.options["third_badge"]

  user_badges = db_get_user_unlocked_badges(ctx.interaction.user.id)

  filtered_badges = [first_badge, second_badge, third_badge] + [b['badge_name'] for b in SPECIAL_BADGES]

  filtered_badge_names = [badge['badge_name'] for badge in user_badges if badge['badge_name'] not in filtered_badges]

  return [b for b in filtered_badge_names if ctx.value.lower() in b.lower()]


# ___________                          _________  
# \__    ___/___   ____    ____   ____ \_   ___ \  ____   ____ 
#   |    | /  _ \ /    \  / ___\ /  _ \/    \  \/ /  _ \ / ___\
#   |    |(  <_> )   |  \/ /_/  >  <_> )     \___(  <_> ) /_/  >
#   |____| \____/|___|  /\___  / \____/ \______  /\____/\___  /
#                     \//_____/                \/      /_____/
class Tongo(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.untradeable_badges = [b['badge_name'] for b in SPECIAL_BADGES]
    self.trade_buttons = [
      pages.PaginatorButton("prev", label="    ⬅     ", style=discord.ButtonStyle.primary, row=1),
      pages.PaginatorButton(
        "page_indicator", style=discord.ButtonStyle.gray, disabled=True, row=1
      ),
      pages.PaginatorButton("next", label="     ➡    ", style=discord.ButtonStyle.primary, row=1),
    ]

  tongo = discord.SlashCommandGroup("tongo", "Commands for Tongo Badge Game")


  #    ______           __
  #   / __/ /____ _____/ /_
  #  _\ \/ __/ _ `/ __/ __/
  # /___/\__/\_,_/_/  \__/
  @tongo.command(
    name="venture",
    description="Begin a game of Tongo!"
  )
  @option(
    name="first_badge",
    description="First badge to add to the pot!",
    required=True,
    autocomplete=risk_autocomplete
  )
  @option(
    name="second_badge",
    description="Second badge to add to the pot!",
    required=True,
    autocomplete=risk_autocomplete
  )
  @option(
    name="third_badge",
    description="Third badge to add to the pot!",
    required=True,
    autocomplete=risk_autocomplete
  )
  @commands.check(access_check)
  async def venture(self, ctx:discord.ApplicationContext, first_badge:str, second_badge:str, third_badge:str):
    await ctx.defer(ephemeral=True)
    user_discord_id = ctx.interaction.user.id
    user_member = await self.bot.current_guild.fetch_member(user_discord_id)
    active_tongo = db_get_active_tongo()

    if active_tongo:
      await ctx.respond(embed=discord.Embed(
          title="Tongo Already In Progress",
          description="There's already an ongoing tongo game!\n\nUse `/tongo risk` to join!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    selected_badges = [first_badge, second_badge, third_badge]
    unlocked_user_badges = db_get_user_unlocked_badges(user_discord_id)
    unlocked_user_badge_names = [b['badge_name'] for b in unlocked_user_badges]

    selected_user_badges = [b for b in selected_badges if b in unlocked_user_badge_names]

    if not await self._validate_selected_user_badges(ctx, selected_user_badges):
      return

    # Validation Passed - Continue
    # Create new tongo entry
    tongo_id = db_create_new_tongo(user_discord_id)
    # Transfer badges to the pot
    db_add_badges_to_pot(user_discord_id, selected_user_badges)
    # Associate player with the new game
    db_add_player_to_tongo(user_discord_id, tongo_id)
    # Cancel any trades involving the user and the badges they threw in
    await self._cancel_tongo_related_trades(user_discord_id, selected_badges)

    tongo_pot_badges = db_get_tongo_pot_badges()

    confirmation_embed = discord.Embed(
      title="TONGO!",
      description=f"A new Tongo game has begun!!!\n\n**{user_member.display_name}** has kicked things off!",
      color=discord.Color.dark_purple()
    )
    confirmation_embed.add_field(
      name=f"Badges Bought In By {user_member.display_name}",
      value="\n".join([f"* {b}" for b in selected_user_badges])
    )
    confirmation_embed.add_field(
      name=f"Current Pot (May Include Extra Badges From Previous Games!)",
      value="\n".join([f"* {b['badge_name']}" for b in tongo_pot_badges])
    )
    confirmation_embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}"
    )
    await ctx.channel.send(embed=confirmation_embed)


  #    ___       _
  #   / _ \___ _(_)__ ___
  #  / , _/ _ `/ (_-</ -_)
  # /_/|_|\_,_/_/___/\__/
  @tongo.command(
    name="risk",
    description="Join the current game of Tongo!"
  )
  @option(
    name="first_badge",
    description="First badge to add to the pot!",
    required=True,
    autocomplete=risk_autocomplete
  )
  @option(
    name="second_badge",
    description="Second badge to add to the pot!",
    required=True,
    autocomplete=risk_autocomplete
  )
  @option(
    name="third_badge",
    description="Third badge to add to the pot!",
    required=True,
    autocomplete=risk_autocomplete
  )
  @commands.check(access_check)
  async def risk(self, ctx:discord.ApplicationContext, first_badge:str, second_badge:str, third_badge:str):
    await ctx.defer(ephemeral=True)
    user_discord_id = ctx.interaction.user.id
    user_member = await self.bot.current_guild.fetch_member(user_discord_id)
    active_tongo = db_get_active_tongo()
    tongo_players = db_get_active_tongo_players(active_tongo['id'])
    tongo_player_ids = [int(p['user_discord_id']) for p in tongo_players]

    if not active_tongo:
      await ctx.respond(embed=discord.Embed(
          title="No Tongo Game In Progress",
          description="No one is playing Tongo yet!\n\nUse `/tongo venture` to begin a game!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return
    elif user_discord_id in tongo_player_ids:
      description = "Damn player, you've already bought in!"
      if user_discord_id == active_tongo['initiator_discord_id']:
        description += f"\n\nPlus you're the one that started it! If you want to deal em out, use `/tongo deal`!"
      await ctx.respond(embed=discord.Embed(
          title="You're Already In The Game!",
          description=description,
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    selected_badges = [first_badge, second_badge, third_badge]
    unlocked_user_badges = db_get_user_unlocked_badges(user_discord_id)
    unlocked_user_badge_names = [b['badge_name'] for b in unlocked_user_badges]

    selected_user_badges = [b for b in selected_badges if b in unlocked_user_badge_names]

    if not await self._validate_selected_user_badges(ctx, selected_user_badges):
      return

    # Validation passed - continue
    # Transfer badges to the pot
    db_add_badges_to_pot(user_discord_id, selected_user_badges)
    # Associate player with the new game
    db_add_player_to_tongo(user_discord_id, active_tongo['id'])
    # Cancel any trades involving the user and the badges they threw in
    await self._cancel_tongo_related_trades(user_discord_id, selected_badges)

    tongo_pot_badges = db_get_tongo_pot_badges()
    tongo_player_members = [await self.bot.current_guild.fetch_member(id) for id in tongo_player_ids]

    confirmation_embed = discord.Embed(
      title="TONGO!",
      description=f"A new challenger appears! **{user_member.display_name}** has joined the table!",
      color=discord.Color.dark_purple()
    )
    confirmation_embed.add_field(
      name=f"Badges Thrown In By {user_member.display_name}",
      value="\n".join([f"* {b}" for b in selected_user_badges])
    )
    confirmation_embed.add_field(
      name=f"Current Players",
      value="\n".join([f"* {m.display_name}" for m in tongo_player_members])
    )
    confirmation_embed.add_field(
      name=f"Total Badges In The Pot",
      value="\n".join([f"* {b['badge_name']}" for b in tongo_pot_badges])
    )
    confirmation_embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}"
    )
    await ctx.channel.send(embed=confirmation_embed)

  async def _cancel_tongo_related_trades(self, user_discord_id, selected_badges):
    # These are all the active or pending trades that involved the user as either the 
    # requestee or requestor and include the badges that were added to the tongo pot
    # are thus no longer valid and need to be canceled
    trades_to_cancel = db_get_related_tongo_badge_trades(user_discord_id, selected_badges)

    # Iterate through to cancel, and then
    for trade in trades_to_cancel:
      db_cancel_trade(trade)
      requestee = await self.bot.current_guild.fetch_member(trade['requestee_id'])
      requestor = await self.bot.current_guild.fetch_member(trade['requestor_id'])

      offered_badge_names, requested_badge_names = get_offered_and_requested_badge_names(trade)

      # Give notice to Requestee
      user = get_user(requestee.id)
      if user["receive_notifications"] and trade['status'] == 'active':
        try:
          requestee_embed = discord.Embed(
            title="Trade Canceled",
            description=f"Just a heads up! Your USS Hood Badge Trade initiated by **{requestor.display_name}** was canceled because one or more of the badges involved were added to the Tongo pot!",
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
      user = get_user(requestor.id)
      if user["receive_notifications"]:
        try:
          requestor_embed = discord.Embed(
            title="Trade Canceled",
            description=f"Just a heads up! Your USS Hood Badge Trade requested from **{requestee.display_name}** was canceled because one or more of the badges involved were added to the Tongo pot!",
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


  #   __  ____  _ ___ __  _
  #  / / / / /_(_) (_) /_(_)__ ___
  # / /_/ / __/ / / / __/ / -_|_-<
  # \____/\__/_/_/_/\__/_/\__/___/
  async def _validate_selected_user_badges(self, ctx:discord.ApplicationContext, selected_user_badges):
    if len(selected_user_badges) != 3:
      await ctx.followup.send(embed=discord.Embed(
        title="Invalid Selection",
        description=f"You must own all of the badges you've selected to risk and they must be unlocked!",
        color=discord.Color.red()
      ), ephemeral=True)
      return False

    if len(selected_user_badges) > len(set(selected_user_badges)):
      await ctx.followup.send(embed=discord.Embed(
        title="Invalid Selection",
        description=f"All badges selected must be unique!",
        color=discord.Color.red()
      ), ephemeral=True)
      return False

    restricted_badges = [b for b in selected_user_badges if b in [b['badge_name'] for b in SPECIAL_BADGES]]
    if restricted_badges:
      await ctx.followup.send(embed=discord.Embed(
        title="Invalid Selection",
        description=f"You cannot risk with the following: {','.join(restricted_badges)}!",
        color=discord.Color.red()
      ), ephemeral=True)
      return False

    return True


# ________                      .__
# \_____  \  __ __   ___________|__| ____   ______
#  /  / \  \|  |  \_/ __ \_  __ \  |/ __ \ /  ___/
# /   \_/.  \  |  /\  ___/|  | \/  \  ___/ \___ \
# \_____\ \_/____/  \___  >__|  |__|\___  >____  >
#        \__>           \/              \/     \/
def db_get_active_tongo():
  with AgimusDB(dictionary=True) as query:
    sql = "SELECT * FROM tongo WHERE status = 'active'"
    query.execute(sql)
    trades = query.fetchone()
  return trades

def db_get_tongo_pot_badges():
  with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT * FROM badge_info AS b_i
        JOIN tongo_pot AS t_p
          ON t_p.badge_filename = b_i.badge_filename
          ORDER BY b_i.badge_name ASC
    '''
    query.execute(sql)
    badges = query.fetchall()
  return badges

def db_get_active_tongo_players(tongo_id):
  with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT * FROM tongo_players AS t_pl
        JOIN tongo AS t
          ON t_pl.tongo_id = t.id
          WHERE t.id = %s
          ORDER BY t_pl.time_created ASC
    '''
    vals = (tongo_id,)
    query.execute(sql, vals)
    players = query.fetchall()
  return players

def db_create_new_tongo(user_discord_id):
  with AgimusDB(dictionary=True) as query:
    sql = '''
      INSERT INTO tongo (initiator_discord_id) VALUES (%s)
    '''
    vals = (user_discord_id,)
    query.execute(sql, vals)
    result = query.lastrowid
  return result

def db_add_player_to_tongo(user_discord_id, tongo_id):
  with AgimusDB(dictionary=True) as query:
    sql = '''
      INSERT INTO tongo_players (user_discord_id, tongo_id) VALUES (%s, %s)
    '''
    vals = (user_discord_id, tongo_id)
    query.execute(sql, vals)
    result = query.lastrowid
  return result

def db_add_badges_to_pot(user_discord_id, selected_user_badges):
  badges_to_add = [db_get_badge_info_by_name(b) for b in selected_user_badges]

  with AgimusDB(dictionary=True) as query:
    # Transfer Badges to Pot
    sql = '''
      INSERT INTO tongo_pot (origin_user_discord_id, badge_filename)
        VALUES
          (%s, %s),
          (%s, %s),
          (%s, %s)
    '''
    vals = (
      user_discord_id, badges_to_add[0]['badge_filename'],
      user_discord_id, badges_to_add[1]['badge_filename'],
      user_discord_id, badges_to_add[2]['badge_filename']
    )
    query.execute(sql, vals)

    # Remove Badges from User
    sql = '''
      DELETE FROM badges
        WHERE (user_discord_id, badge_filename)
        IN (
          (%s,%s),
          (%s,%s),
          (%s,%s)
        )
    '''
    vals = (
      user_discord_id, badges_to_add[0]['badge_filename'],
      user_discord_id, badges_to_add[1]['badge_filename'],
      user_discord_id, badges_to_add[2]['badge_filename']
    )
    query.execute(sql, vals)

def db_get_related_tongo_badge_trades(user_discord_id, selected_user_badges):
  related_badges = [db_get_badge_info_by_name(b) for b in selected_user_badges]

  with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT t.*

      FROM trades as t
      LEFT JOIN trade_offered `to` ON t.id = to.trade_id
      LEFT JOIN trade_requested `tr` ON t.id = tr.trade_id

      -- pending or active
      WHERE t.status IN ('pending','active')

      -- involves one or more of the users involved in the active trade
      AND (t.requestor_id = %s OR t.requestee_id = %s)

      -- involves one or more of the badges involved in the active trade
      AND (to.badge_filename IN (%s, %s, %s) OR tr.badge_filename IN (%s, %s, %s))
      GROUP BY t.id
    '''
    vals = (
      user_discord_id, user_discord_id,
      related_badges[0]['badge_filename'], related_badges[1]['badge_filename'], related_badges[2]['badge_filename'],
      related_badges[0]['badge_filename'], related_badges[1]['badge_filename'], related_badges[2]['badge_filename']
    )
    query.execute(sql, vals)
    trades = query.fetchall()
  return trades
