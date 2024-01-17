from common import *
from queries.wishlist import db_get_user_wishlist_badges
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
    self.first_auto_confront = True

  tongo = discord.SlashCommandGroup("tongo", "Commands for Tongo Badge Game")

  #   _   __         __ 
  #  | | / /__ ___  / /___ _________
  #  | |/ / -_) _ \/ __/ // / __/ -_)
  #  |___/\__/_//_/\__/\_,_/_/  \__/
  @tongo.command(
    name="venture",
    description="Begin a game of Tongo!"
  )
  @option(
    name="first_badge",
    description="First badge to add to The Great Material Continuum!",
    required=True,
    autocomplete=risk_autocomplete
  )
  @option(
    name="second_badge",
    description="Second badge to add to The Great Material Continuum!",
    required=True,
    autocomplete=risk_autocomplete
  )
  @option(
    name="third_badge",
    description="Third badge to add to The Great Material Continuum!",
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
      title="TONGO! Badges Ventured!",
      description=f"A new Tongo game has begun!!!\n\n**{user_member.display_name}** has kicked things off and is The Chair!\n\n"
                  "Only *they* have the ability to end the game via `/tongo confront`!\n\n"
                  f"If **{user_member.display_name}** does not Confront within 8 hours, this game will automatically end and "
                  "the badge distribution from The Continium will automatically occur!",
      color=discord.Color.dark_purple()
    )
    confirmation_embed.add_field(
      name=f"Badges Ventured By {user_member.display_name}",
      value="\n".join([f"* {b}" for b in selected_user_badges]),
      inline=False
    )
    confirmation_embed.add_field(
      name=f"The Great Material Continuum",
      value="\n".join([f"* {b['badge_name']}" for b in tongo_pot_badges]),
      inline=False
    )
    confirmation_embed.set_image(url="https://i.imgur.com/tRi1vYq.gif")
    confirmation_embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
      icon_url="https://i.imgur.com/GTN4gQG.jpg"
    )
    await ctx.channel.send(embed=confirmation_embed)
    self.first_auto_confront = True
    self.auto_confront.start()

  #    ___  _     __
  #   / _ \(_)__ / /__
  #  / , _/ (_-</  '_/
  # /_/|_/_/___/_/\_\
  @tongo.command(
    name="risk",
    description="Risk some badges and join the current game of Tongo!"
  )
  @option(
    name="first_badge",
    description="First badge to add to The Great Material Continuum!",
    required=True,
    autocomplete=risk_autocomplete
  )
  @option(
    name="second_badge",
    description="Second badge to add to The Great Material Continuum!",
    required=True,
    autocomplete=risk_autocomplete
  )
  @option(
    name="third_badge",
    description="Third badge to add to The Great Material Continuum!",
    required=True,
    autocomplete=risk_autocomplete
  )
  @commands.check(access_check)
  async def risk(self, ctx:discord.ApplicationContext, first_badge:str, second_badge:str, third_badge:str):
    user_discord_id = ctx.interaction.user.id
    user_member = await self.bot.current_guild.fetch_member(user_discord_id)
    active_tongo = db_get_active_tongo()

    if not active_tongo:
      await ctx.respond(embed=discord.Embed(
          title="No Tongo Game In Progress",
          description="No one is playing Tongo yet!\n\nUse `/tongo venture` to begin a game!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    tongo_players = db_get_active_tongo_players(active_tongo['id'])
    tongo_player_ids = [int(p['user_discord_id']) for p in tongo_players]
    if user_discord_id in tongo_player_ids:
      description = "Damn player, you've already made your Risk!"
      if user_discord_id == active_tongo['chair_discord_id']:
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
    tongo_player_ids.append(user_discord_id)
    tongo_player_members = [await self.bot.current_guild.fetch_member(id) for id in tongo_player_ids]

    confirmation_embed = discord.Embed(
      title="TONGO! Badges Risked!",
      description=f"### **{user_member.display_name}** has joined the table!\n\nA new challenger appears!",
      color=discord.Color.dark_purple()
    )
    confirmation_embed.add_field(
      name=f"Badges Risked By {user_member.display_name}",
      value="\n".join([f"* {b}" for b in selected_user_badges]),
      inline=False
    )
    confirmation_embed.add_field(
      name=f"Current Players",
      value="\n".join([f"* {m.display_name}" for m in tongo_player_members]),
      inline=False
    )
    confirmation_embed.add_field(
      name=f"Total Badges In The Great Material Continuum!",
      value="\n".join([f"* {b['badge_name']}" for b in tongo_pot_badges]),
      inline=False
    )
    confirmation_embed.set_image(url="https://i.imgur.com/iX9ZCpH.gif")
    confirmation_embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
      icon_url="https://i.imgur.com/GTN4gQG.jpg"
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

  #    ____        __
  #   /  _/__  ___/ /____ __
  #  _/ // _ \/ _  / -_) \ /
  # /___/_//_/\_,_/\__/_\_\
  @tongo.command(
    name="index",
    description="Check the current status of the active game of Tongo!"
  )
  @commands.check(access_check)
  async def index(self, ctx:discord.ApplicationContext):
    user_discord_id = ctx.interaction.user.id
    user_member = await self.bot.current_guild.fetch_member(user_discord_id)
    active_tongo = db_get_active_tongo()

    if not active_tongo:
      await ctx.respond(embed=discord.Embed(
          title="No Tongo Game In Progress",
          description="No one is playing Tongo yet!\n\nUse `/tongo venture` to begin a game!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    active_tongo_chair_id = int(active_tongo['chair_discord_id'])
    active_chair_member = await self.bot.current_guild.fetch_member(active_tongo_chair_id)

    tongo_players = db_get_active_tongo_players(active_tongo['id'])
    tongo_player_ids = [int(p['user_discord_id']) for p in tongo_players]
    tongo_player_members = [await self.bot.current_guild.fetch_member(id) for id in tongo_player_ids]

    tongo_pot_badges = db_get_tongo_pot_badges()

    description=f"Index requested by **{user_member.display_name}**!\n\nDisplaying the status of the current game of Tongo!\n\n"
    if self.auto_confront.next_iteration:
      current_time = datetime.now(timezone.utc)
      remaining_time = current_time - self.auto_confront.next_iteration
      description += f"This Tongo game has {humanize.naturaltime(remaining_time, minimum_unit='minutes')} left before the game is automatically ended!"

    confirmation_embed = discord.Embed(
      title="TONGO! Call For Index!",
      description=description,
      color=discord.Color.dark_purple()
    )
    confirmation_embed.add_field(
      name=f"Tongo Chair",
      value=f"* {active_chair_member.display_name}",
      inline=False
    )
    confirmation_embed.add_field(
      name=f"Current Players",
      value="\n".join([f"* {m.display_name}" for m in tongo_player_members]),
      inline=False
    )
    confirmation_embed.add_field(
      name=f"Total Badges In The Great Material Continuum!",
      value="\n".join([f"* {b['badge_name']}" for b in tongo_pot_badges]),
      inline=False
    )
    confirmation_embed.set_image(url="https://i.imgur.com/aWLYGKQ.gif")
    confirmation_embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
      icon_url="https://i.imgur.com/GTN4gQG.jpg"
    )
    await ctx.channel.send(embed=confirmation_embed)
    await ctx.respond(embed=discord.Embed(
        title="Index Request Processed!",
        color=discord.Color.dark_purple()
      ), ephemeral=True
    )

  #   _____          ___              __
  #  / ___/__  ___  / _/______  ___  / /_
  # / /__/ _ \/ _ \/ _/ __/ _ \/ _ \/ __/
  # \___/\___/_//_/_//_/  \___/_//_/\__/
  @tongo.command(
    name="confront",
    description="If you're The Chair, end the current game of Tongo!"
  )
  @commands.check(access_check)
  async def confront(self, ctx:discord.ApplicationContext):
    user_discord_id = ctx.interaction.user.id
    active_tongo = db_get_active_tongo()

    if not active_tongo:
      await ctx.respond(embed=discord.Embed(
          title="No Tongo Game In Progress",
          description="No one is playing Tongo yet!\n\nUse `/tongo venture` to begin a game!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return
    else:
      active_tongo_chair_id = int(active_tongo['chair_discord_id'])
      active_chair = await bot.current_guild.fetch_member(active_tongo_chair_id)
      if active_tongo_chair_id != user_discord_id:
        await ctx.respond(embed=discord.Embed(
            title="You're Not The Chair!",
            description=f"Only The Chair is allowed to end the Tongo!\n\nThe current Chair is: **{active_chair.display_name}**",
            color=discord.Color.red()
          ),
          ephemeral=True
        )
        return

    # Cancel the auto_confront that was started when the venture was fired
    self.auto_confront.cancel()

    tongo_players = db_get_active_tongo_players(active_tongo['id'])
    tongo_player_ids = [int(p['user_discord_id']) for p in tongo_players]

    if len(tongo_player_ids) < 2:
      await ctx.respond(embed=discord.Embed(
          title="You're The Only Player!",
          description="Can't do a Confront when you're the only player in the game! Invite some people!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    # Respond to command required
    await ctx.respond(embed=discord.Embed(
        title="Confront Acknowledged!",
        color=discord.Color.dark_purple()
      ), ephemeral=True
    )

    results = await self._perform_confront_distribution()
    tongo_pot_badges = db_get_tongo_pot_badges()
    results_embed = discord.Embed(
      title="TONGO! Complete!",
      color=discord.Color.dark_purple()
    )
    if tongo_pot_badges:
      results_embed.add_field(
        name=f"Remaining Badges In The Great Material Continuum!",
        value="\n".join([f"* {b['badge_name']}" for b in tongo_pot_badges]),
        inline=False
      )
    results_embed.set_image(url="https://i.imgur.com/gdpvba5.gif")
    channel_message = await ctx.channel.send(embed=results_embed)

    for result in results.items():
      player_user_discord_id = result[0]
      player_member = await self.bot.current_guild.fetch_member(player_user_discord_id)
      player_badges_received = [db_get_badge_info_by_filename(b) for b in list(result[1])]
      player_wishlist = db_get_user_wishlist_badges(player_user_discord_id)

      if len(player_badges_received) > 0:
        won_badge_filenames = [b['badge_filename'] for b in player_badges_received]
        won_image_id = f"{active_tongo['id']}-won-{result[0]}"
        won_image = await generate_badge_trade_showcase(
          won_badge_filenames,
          won_image_id,
          f"Badges Won By {player_member.display_name}",
          f"{len(player_badges_received)} Badges"
        )

        player_embed = discord.Embed(
          title=f"{player_member.display_name} Received:",
          description="\n".join([f"* {b['badge_name']}" for b in player_badges_received]),
          color=discord.Color.dark_purple()
        )
        wishlist_badges_received = [b for b in player_wishlist if b['badge_filename'] in [b['badge_filename'] for b in player_badges_received]]
        if wishlist_badges_received:
          player_embed.add_field(
            name="Wishlisted Badges Received",
            value="\n".join([f"* {b['badge_name']}" for b in wishlist_badges_received])
          )
          db_purge_users_wishlist(player_user_discord_id)
        player_embed.set_image(url=f"attachment://{won_image_id}.png")
        await ctx.channel.send(embed=player_embed, file=won_image)
        
        # Now send message to the player
        player_message_embed = discord.Embed(
          title=f"TONGO! Confront!",
          description="Your Tongo game has ended! Your winnings are included below, "
                      f"and you can view the full results at: {channel_message.jump_url}",
          color=discord.Color.dark_purple()
        )
        player_message_embed.add_field(
          name=f"Badges Acquired",
          value="\n".join([f"* {b['badge_name']}" for b in player_badges_received])
        )
        if wishlist_badges_received:
          player_message_embed.add_field(
            name="Wishlisted Badges Received",
            value="\n".join([f"* {b['badge_name']}" for b in wishlist_badges_received])
          )
        try:
          await player_member.send(embed=player_message_embed)
        except discord.Forbidden as e:
          logger.info(f"Unable to send Tongo completion message to {player_member.display_name}, they have their DMs closed.")
          pass
      else:
        player_embed = discord.Embed(
          title=f"{player_member.display_name} Did Not Receive Any Badges..."
        )
        player_embed.set_image(url="https://i.imgur.com/qZNBAvE.gif")
        await ctx.channel.send(embed=player_embed)
        
        # Now send message to the player
        player_message_embed = discord.Embed(
          title=f"TONGO! Confront!",
          description="Your Tongo game has ended! Sadly you did not receive any badges... \n\n"
                      f"You can view the full results at: {channel_message.jump_url}",
          color=discord.Color.dark_purple()
        )
        player_message_embed.set_image(url="https://i.imgur.com/qZNBAvE.gif")
        try:
          await player_member.send(embed=player_message_embed)
        except discord.Forbidden as e:
          logger.info(f"Unable to send Tongo completion message to {player_member.display_name}, they have their DMs closed.")
          pass

    self.auto_confront.cancel()
    # We're Done Baybee!

  @tasks.loop(hours=8)
  async def auto_confront(self):
    if self.first_auto_confront:
      self.first_auto_confront = False
      return

    active_tongo = db_get_active_tongo()

    if not active_tongo:
      self.auto_confront.cancel()
      return

    tongo_players = db_get_active_tongo_players(active_tongo['id'])
    active_tongo_chair_id = int(active_tongo['chair_discord_id'])
    active_chair = await bot.current_guild.fetch_member(active_tongo_chair_id)

    # If we never got enough players, end the game and notify the chair
    if len(tongo_players) < 2:
      db_end_current_tongo(active_tongo['id'])
      try:
        canceled_embed = discord.Embed(
          title="TONGO! Auto-Canceled!",
          description=f"Hey there {active_chair.display_name}, looks like time ran out on your Tongo game and there were not "
                "enough players. Your game has been automatically canceled.",
          color=discord.Color.red()
        )
        canceled_embed.set_footer(
          text="Note: You can use /settings to enable or disable these messages."
        )
        await active_chair.send(embed=canceled_embed)
      except discord.Forbidden as e:
        logger.info(f"Unable to Tongo auto-cancel message to {active_chair.display_name}, they have their DMs closed.")
        pass
      return

    results = await self._perform_confront_distribution()
    tongo_pot_badges = db_get_tongo_pot_badges()
    results_embed = discord.Embed(
      title="TONGO! Game Automatically Ending!",
      description=f"Whoops, **{active_chair.display_name}** failed to Confront before the time ran out!\n\nEnding the game!",
      color=discord.Color.dark_purple()
    )
    if tongo_pot_badges:
      results_embed.add_field(
        name=f"Remaining Badges In The Great Material Continuum!",
        value="\n".join([f"* {b['badge_name']}" for b in tongo_pot_badges]),
        inline=False
      )
    results_embed.set_image(url="https://i.imgur.com/gdpvba5.gif")
    trade_channel = await self.bot.fetch_channel(get_channel_id("bahrats-bazaar"))
    channel_message = await trade_channel.send(embed=results_embed)

    for result in results.items():
      player_user_discord_id = result[0]
      player_member = await self.bot.current_guild.fetch_member(player_user_discord_id)
      player_badges_received = [db_get_badge_info_by_filename(b) for b in list(result[1])]
      player_wishlist = db_get_user_wishlist_badges(player_user_discord_id)

      if len(player_badges_received) > 0:
        won_badge_filenames = [b['badge_filename'] for b in player_badges_received]
        won_image_id = f"{active_tongo['id']}-won-{result[0]}"
        won_image = await generate_badge_trade_showcase(
          won_badge_filenames,
          won_image_id,
          f"Badges Won By {player_member.display_name}",
          f"{len(player_badges_received)} Badges"
        )

        player_embed = discord.Embed(
          title=f"{player_member.display_name} Received:",
          description="\n".join([f"* {b['badge_name']}" for b in player_badges_received]),
          color=discord.Color.dark_purple()
        )
        wishlist_badges_received = [b for b in player_wishlist if b['badge_filename'] in [b['badge_filename'] for b in player_badges_received]]
        if wishlist_badges_received:
          player_embed.add_field(
            name="Wishlisted Badges Received",
            value="\n".join([f"* {b['badge_name']}" for b in wishlist_badges_received])
          )
          db_purge_users_wishlist(player_user_discord_id)
        player_embed.set_image(url=f"attachment://{won_image_id}.png")
        await trade_channel.send(embed=player_embed, file=won_image)

        # Now send message to the player
        player_message_embed = discord.Embed(
          title=f"TONGO! Game Automatically Ending!",
          description="Time ran out for your Tongo game and it has automatically ended! Your winnings are included below, "
                      f"and you can view the full results at: {channel_message.jump_url}",
          color=discord.Color.dark_purple()
        )
        player_message_embed.add_field(
          name=f"Badges Acquired",
          value="\n".join([f"* {b['badge_name']}" for b in player_badges_received])
        )
        if wishlist_badges_received:
          player_message_embed.add_field(
            name="Wishlisted Badges Received",
            value="\n".join([f"* {b['badge_name']}" for b in wishlist_badges_received])
          )
        try:
          await player_member.send(embed=player_message_embed)
        except discord.Forbidden as e:
          logger.info(f"Unable to send Tongo completion message to {player_member.display_name}, they have their DMs closed.")
          pass
      else:
        player_embed = discord.Embed(
          title=f"{player_member.display_name} Did Not Receive Any Badges!"
        )
        player_message_embed.set_image(url="https://i.imgur.com/qZNBAvE.gif")
        await trade_channel.send(embed=player_embed)

        # Now send message to the player
        player_message_embed = discord.Embed(
          title=f"TONGO! Confront!",
          description="Your Tongo game has automatically ended! Sadly you did not receive any badges... \n\n"
                      f"You can view the full results at: {channel_message.jump_url}",
          color=discord.Color.dark_purple()
        )
        player_message_embed.set_image(url="https://i.imgur.com/qZNBAvE.gif")
        try:
          await player_member.send(embed=player_message_embed)
        except discord.Forbidden as e:
          logger.info(f"Unable to send Tongo completion message to {player_member.display_name}, they have their DMs closed.")
          pass

    self.auto_confront.cancel()

  async def _perform_confront_distribution(self):
    active_tongo = db_get_active_tongo()
    tongo_players = db_get_active_tongo_players(active_tongo['id'])
    tongo_player_ids = [int(p['user_discord_id']) for p in tongo_players]
    tongo_pot_badges = db_get_tongo_pot_badges()
    tongo_pot = [b['badge_filename'] for b in tongo_pot_badges]

    player_distribution = { player_id: set() for player_id in tongo_player_ids }
    player_inventories = {}
    for player_id in tongo_player_ids:
      player_inventories[player_id] = [b['badge_filename'] for b in db_get_user_badges(player_id)]

    random.shuffle(tongo_pot)

    # We're going to go round-robin and try to distribute all of the shuffled badges
    turn_index = 0
    while tongo_pot:
      # logger.info(f"Turn Index Is: {turn_index}")
      working_pot = tongo_pot.copy()
      
      current_player_id = tongo_player_ids[turn_index % len(tongo_player_ids)]
      current_badge = working_pot.pop(0)

      # logger.info(f"Current player: {current_player_id}")

      # Check if the player already reached the maximum badges per player
      if len(player_distribution[current_player_id]) >= 3:
          # logger.info(f"Current player: {current_player_id} has reached the 3 badge limit")
          # if the current player has reached the limit
          turn_index += 1
          break

      # Check if the player already has all remaining badges
      if all(b in player_distribution[current_player_id] for b in player_inventories[current_player_id]):
          # logger.info(f"Current player: {current_player_id} already has all the badges either via the distribution, or in their existing inventory.")
          # Move to the next player
          break

      # Check if the player already has the badge
      while (current_badge in player_distribution[current_player_id]) or (current_badge in player_inventories[current_player_id]):
          if not working_pot:
              # If no more badges are available, exit
              # logger.info(f"No badges left to attempt to give to Player {current_player_id}! End the turn.")
              break
          # If they have the badge, try the next one
          previous_badge = current_badge
          current_badge = working_pot.pop(0)
          # logger.info(f"Player already has {previous_badge}, pop off the next one: {current_badge}")

      # Check if the player received a badge
      if current_badge not in player_distribution[current_player_id] and current_badge not in player_inventories[current_player_id]:
          player_distribution[current_player_id].add(current_badge)
          tongo_pot.remove(current_badge)
          #logger.info(f"{current_player_id} received badge: {current_badge}")

      turn_index += 1
      # logger.info(f"Moving to the next turn: {turn_index}")

    # Now go through the distribution and actually perform the db handouts and removal from the pot
    for p in player_distribution.items():
      player_id = p[0]
      player_badges = p[1]

      for b in player_badges:
        db_grant_player_badge(player_id, b)
        db_remove_badge_from_pot(b)

    # End the current game of tongo
    db_end_current_tongo(active_tongo['id'])

    return player_distribution

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

    tongo_pot_badges = db_get_tongo_pot_badges()
    existing_pot_badges = [b for b in selected_user_badges if b in [b['badge_name'] for b in tongo_pot_badges]]
    if existing_pot_badges:
      await ctx.followup.send(embed=discord.Embed(
        title="Invalid Selection",
        description=f"The following badges are already in The Great Material Continuum: {','.join(existing_pot_badges)}!",
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
      INSERT INTO tongo (chair_discord_id) VALUES (%s)
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

def db_grant_player_badge(user_discord_id, badge_filename):
  with AgimusDB() as query:
    sql = "INSERT INTO badges (user_discord_id, badge_filename) VALUES (%s, %s)"
    vals = (user_discord_id, badge_filename)
    query.execute(sql, vals)

def db_remove_badge_from_pot(badge_filename):
  with AgimusDB() as query:
    sql = "DELETE FROM tongo_pot WHERE badge_filename = %s"
    vals = (badge_filename,)
    query.execute(sql, vals)

def db_end_current_tongo(tongo_id):
  with AgimusDB() as query:
    sql = "UPDATE tongo SET status = 'complete' WHERE id = %s"
    vals = (tongo_id,)
    query.execute(sql, vals)
