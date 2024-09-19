from common import *
from handlers.xp import increment_user_xp
from queries.wishlist import db_get_user_wishlist_badges, db_autolock_badges_by_filenames_if_in_wishlist
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
  randomized = ctx.options['randomized']
  if randomized:
    return ["Error: This field cannot be selected if 'random' has been selected."]

  first_badge = ctx.options["first_badge"]
  second_badge = ctx.options["second_badge"]
  third_badge = ctx.options["third_badge"]

  user_badges = await db_get_user_unlocked_badges(ctx.interaction.user.id)
  if not user_badges:
    return ["Error: You don't have any Unlocked Badges!"]

  tongo_pot = await db_get_tongo_pot_badges()

  special_badges = await db_get_special_badges()
  filtered_badges = [first_badge, second_badge, third_badge] + [b['badge_name'] for b in tongo_pot] + [b['badge_name'] for b in special_badges]

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
    name="randomized",
    description="Select random badges from your Unlocked Badge inventory?",
    required=True,
    type=bool
  )
  @option(
    name="first_badge",
    description="First badge to add to The Great Material Continuum!",
    required=False,
    autocomplete=risk_autocomplete
  )
  @option(
    name="second_badge",
    description="Second badge to add to The Great Material Continuum!",
    required=False,
    autocomplete=risk_autocomplete
  )
  @option(
    name="third_badge",
    description="Third badge to add to The Great Material Continuum!",
    required=False,
    autocomplete=risk_autocomplete
  )
  @commands.check(access_check)
  async def venture(self, ctx:discord.ApplicationContext, randomized:bool, first_badge:str, second_badge:str, third_badge:str):
    await ctx.defer(ephemeral=True)
    user_discord_id = ctx.interaction.user.id
    user_member = await self.bot.current_guild.fetch_member(user_discord_id)
    active_tongo = await db_get_active_tongo()

    if active_tongo:
      await ctx.followup.send(embed=discord.Embed(
          title="Tongo Already In Progress",
          description="There's already an ongoing tongo game!\n\nUse `/tongo risk` to join!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    selected_badge_names = [first_badge, second_badge, third_badge]
    unlocked_user_badges = await db_get_user_unlocked_badges(user_discord_id)
    unlocked_user_badge_names = [b['badge_name'] for b in unlocked_user_badges]
    if randomized:
      if "Error: This field cannot be selected if 'random' has been selected." in selected_badge_names or "" in selected_badge_names:
        await ctx.followup.send(embed=discord.Embed(
            title="Invalid Badge Selection",
            description="One or more of the Badge options entered are entirely invalid, please try again",
            color=discord.Color.red()
          ),
          ephemeral=True
        )
        return

      tongo_pot_badges = await db_get_tongo_pot_badges()
      tongo_pot_badge_names = [b['badge_name'] for b in tongo_pot_badges]
      if all(b in tongo_pot_badge_names for b in unlocked_user_badge_names):
        description = "All of the Unlocked Badges you possess are already in the Continuum!"
        if len(unlocked_user_badge_names) == 0:
          description = "You don't possess any Unlocked Badges!"
        await ctx.followup.send(embed=discord.Embed(
            title="No Badges Viable For Random Selection!",
            description=description,
            color=discord.Color.red()
          ).set_footer(text="Try unlocking some others!"),
          ephemeral=True
        )
        return

      special_badges = await db_get_special_badges()
      selectable_unlocked_badge_names = [b for b in unlocked_user_badge_names if b not in tongo_pot_badge_names and b not in special_badges]
      if len(selectable_unlocked_badge_names) < 3:
        await ctx.followup.send(embed=discord.Embed(
            title="Not Enough Viable Unlocked Badges Available!",
            description=f"You only have {len(selectable_unlocked_badge_names)} available to Randomly Select, you need a minimum of 3!",
            color=discord.Color.red()
          ).set_footer(text="Try unlocking some others!"),
          ephemeral=True
        )
        return

      randomized_badge_names = random.sample(selectable_unlocked_badge_names, 3)
      selected_user_badges = [await db_get_badge_info_by_name(b) for b in randomized_badge_names]
    else:
      selected_user_badge_names = [b for b in selected_badge_names if b in unlocked_user_badge_names]
      selected_user_badges = [await db_get_badge_info_by_name(b) for b in selected_user_badge_names]

      if not await self._validate_selected_user_badges(ctx, selected_user_badge_names):
        return

    # Validation Passed - Continue
    # Responding to the command is required
    await ctx.followup.send(embed=discord.Embed(
        title="Venture Acknowledged!",
        color=discord.Color.dark_purple()
      ), ephemeral=True
    )

    # Create new tongo entry
    tongo_id = await db_create_new_tongo(user_discord_id)
    # Transfer badges to the pot
    await db_add_badges_to_pot(user_discord_id, selected_user_badges)
    # Associate player with the new game
    await db_add_player_to_tongo(user_discord_id, tongo_id)
    # Cancel any trades involving the user and the badges they threw in
    await self._cancel_tongo_related_trades(user_discord_id, selected_user_badges)

    tongo_pot_badges = await db_get_tongo_pot_badges()
    tongo_pot_chunks = [tongo_pot_badges[i:i + 30] for i in range(0, len(tongo_pot_badges), 30)]

    confirmation_embed = discord.Embed(
      title="TONGO! Badges Ventured!",
      description=f"A new Tongo game has begun!!!\n\n**{user_member.display_name}** has kicked things off {' with 3 **RANDOMLY SELECTED** Badges' if randomized else ''} and is The Chair!\n\n"
                  "Only *they* have the ability to end the game via `/tongo confront`!\n\n"
                  f"If **{user_member.display_name}** does not Confront within 8 hours, this game will automatically end and "
                  "the badge distribution from The Continuum will automatically occur!",
      color=discord.Color.dark_purple()
    )
    confirmation_embed.add_field(
      name=f"Badges Ventured By {user_member.display_name}",
      value="\n".join([f"* {b['badge_name']}" for b in selected_user_badges]),
      inline=False
    )
    confirmation_embed.add_field(
      name=f"The Great Material Continuum",
      value="\n".join([f"* {b['badge_name']}" for b in tongo_pot_chunks[0]]),
      inline=False
    )
    confirmation_embed.set_image(url="https://i.imgur.com/tRi1vYq.gif")
    confirmation_embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
      icon_url="https://i.imgur.com/GTN4gQG.jpg"
    )

    continuum_images = await generate_paginated_continuum_images(tongo_pot_badges)
    trade_channel = await self.bot.fetch_channel(get_channel_id("bahrats-bazaar"))
    await trade_channel.send(embed=confirmation_embed)

    if len(tongo_pot_chunks) > 1:
      for t_chunk in tongo_pot_chunks[1:]:
        chunk_embed = discord.Embed(
          title=f"TONGO! Badges Ventured by **{user_member.display_name}** (Continued)!",
          color=discord.Color.dark_purple()
        )
        chunk_embed.add_field(
          name=f"Total Badges In The Great Material Continuum!",
          value="\n".join([f"* {b['badge_name']}" for b in t_chunk]),
          inline=False
        )
        chunk_embed.set_footer(
          text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
          icon_url="https://i.imgur.com/GTN4gQG.jpg"
        )
        await trade_channel.send(embed=chunk_embed)

    await self._send_continuum_images_to_channel(trade_channel, continuum_images)

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
    name="randomized",
    description="Select random badges from your Unlocked Badge inventory?",
    required=True,
    type=bool
  )
  @option(
    name="first_badge",
    description="First badge to add to The Great Material Continuum!",
    required=False,
    autocomplete=risk_autocomplete
  )
  @option(
    name="second_badge",
    description="Second badge to add to The Great Material Continuum!",
    required=False,
    autocomplete=risk_autocomplete
  )
  @option(
    name="third_badge",
    description="Third badge to add to The Great Material Continuum!",
    required=False,
    autocomplete=risk_autocomplete
  )
  @commands.check(access_check)
  async def risk(self, ctx:discord.ApplicationContext, randomized:bool, first_badge, second_badge, third_badge):
    await ctx.defer(ephemeral=True)
    user_discord_id = ctx.interaction.user.id
    user_member = await self.bot.current_guild.fetch_member(user_discord_id)
    active_tongo = await db_get_active_tongo()

    if not active_tongo:
      await ctx.followup.send(embed=discord.Embed(
          title="No Tongo Game In Progress",
          description="No one is playing Tongo yet!\n\nUse `/tongo venture` to begin a game!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    active_tongo_chair_id = int(active_tongo['chair_discord_id'])
    active_chair_member = await self.bot.current_guild.fetch_member(active_tongo_chair_id)

    tongo_players = await db_get_active_tongo_players(active_tongo['id'])
    tongo_player_ids = [int(p['user_discord_id']) for p in tongo_players]
    if user_discord_id in tongo_player_ids:
      description = "Damn player, you've already made your Risk!"
      if user_discord_id == active_tongo_chair_id:
        description += f"\n\nPlus you're the one that started it! If you want to deal em out, use `/tongo confront`!"
      await ctx.followup.send(embed=discord.Embed(
        title="You're Already In The Game!",
        description=description,
        color=discord.Color.red()
      ), ephemeral=True)
      return

    selected_badge_names = [first_badge, second_badge, third_badge]
    unlocked_user_badges = await db_get_user_unlocked_badges(user_discord_id)
    unlocked_user_badge_names = [b['badge_name'] for b in unlocked_user_badges]
    if randomized:
      if "Error: This field cannot be selected if 'random' has been selected." in selected_badge_names or "" in selected_badge_names:
        await ctx.followup.send(embed=discord.Embed(
            title="Invalid Badge Selection",
            description="One or more of the Badge options entered are entirely invalid, please try again",
            color=discord.Color.red()
          ),
          ephemeral=True
        )
        return

      tongo_pot_badges = await db_get_tongo_pot_badges()
      tongo_pot_badge_names = [b['badge_name'] for b in tongo_pot_badges]
      if all(b in tongo_pot_badge_names for b in unlocked_user_badge_names):
        description = "All of the Unlocked Badges you possess are already in the Continuum!"
        if len(unlocked_user_badge_names) == 0:
          description = "You don't possess any Unlocked Badges!"
        await ctx.followup.send(embed=discord.Embed(
            title="No Badges Viable For Random Selection!",
            description=description,
            color=discord.Color.red()
          ).set_footer(text="Try unlocking some others!"),
          ephemeral=True
        )
        return

      special_badges = await db_get_special_badges()
      selectable_unlocked_badge_names = [b for b in unlocked_user_badge_names if b not in tongo_pot_badge_names and b not in special_badges]
      if len(selectable_unlocked_badge_names) < 3:
        await ctx.followup.send(embed=discord.Embed(
            title="Not Enough Viable Unlocked Badges Available!",
            description=f"You only have {len(selectable_unlocked_badge_names)} available to Randomly Select, you need a minimum of 3!",
            color=discord.Color.red()
          ).set_footer(text="Try unlocking some others!"),
          ephemeral=True
        )
        return

      randomized_badge_names = random.sample(selectable_unlocked_badge_names, 3)
      selected_user_badges = [await db_get_badge_info_by_name(b) for b in randomized_badge_names]
    else:
      selected_user_badge_names = [b for b in selected_badge_names if b in unlocked_user_badge_names]
      selected_user_badges = [await db_get_badge_info_by_name(b) for b in selected_user_badge_names]

      if not await self._validate_selected_user_badges(ctx, selected_user_badge_names):
        return

    # Validation Passed - Continue
    # Responding to the command is required
    await ctx.followup.send(embed=discord.Embed(
        title="Risk Acknowledged!",
        color=discord.Color.dark_purple()
      ), ephemeral=True
    )

    tongo_id = active_tongo['id']
    # Transfer badges to the pot
    await db_add_badges_to_pot(user_discord_id, selected_user_badges)
    # Associate player with the new game
    await db_add_player_to_tongo(user_discord_id, tongo_id)
    # Cancel any trades involving the user and the badges they threw in
    await self._cancel_tongo_related_trades(user_discord_id, selected_user_badges)

    tongo_pot_badges = await db_get_tongo_pot_badges()
    tongo_pot_chunks = [tongo_pot_badges[i:i + 30] for i in range(0, len(tongo_pot_badges), 30)]
    tongo_player_ids.append(user_discord_id)
    tongo_player_members = [await self.bot.current_guild.fetch_member(id) for id in tongo_player_ids]

    player_count = len(tongo_player_ids)

    description=f"### **{user_member.display_name}** has joined the table!\n\nA new challenger appears! Player {player_count} has entered the game{' with 3 **RANDOMLY SELECTED** Badges' if randomized else ''}!"
    if self.auto_confront.next_iteration:
      current_time = datetime.now(timezone.utc)
      remaining_time = current_time - self.auto_confront.next_iteration
      description += f"\n\nThis Tongo game has {humanize.naturaltime(remaining_time)} left before the game is automatically ended!"

    confirmation_embed = discord.Embed(
      title="TONGO! Badges Risked!",
      description=description,
      color=discord.Color.dark_purple()
    )
    confirmation_embed.add_field(
      name=f"Badges Risked By {user_member.display_name}",
      value="\n".join([f"* {b['badge_name']}" for b in selected_user_badges]),
      inline=False
    )
    confirmation_embed.add_field(
      name=f"Current Players ({player_count})",
      value="\n".join([f"* {m.display_name}" for m in tongo_player_members]),
      inline=False
    )
    confirmation_embed.add_field(
      name=f"Total Badges In The Great Material Continuum!",
      value="\n".join([f"* {b['badge_name']}" for b in tongo_pot_chunks[0]]),
      inline=False
    )
    gif_url = "https://i.imgur.com/iX9ZCpH.gif"
    if randomized:
      gif_url = "https://i.imgur.com/zEvF7uO.gif"
    confirmation_embed.set_image(url=gif_url)
    confirmation_embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
      icon_url="https://i.imgur.com/GTN4gQG.jpg"
    )

    continuum_images = await generate_paginated_continuum_images(tongo_pot_badges)
    trade_channel = await self.bot.fetch_channel(get_channel_id("bahrats-bazaar"))
    await trade_channel.send(embed=confirmation_embed)

    if len(tongo_pot_chunks) > 1:
      for t_chunk in tongo_pot_chunks[1:]:
        chunk_embed = discord.Embed(
          title=f"Index requested by **{user_member.display_name}** (Continued)",
          color=discord.Color.dark_purple()
        )
        chunk_embed.add_field(
          name=f"Total Badges In The Great Material Continuum!",
          value="\n".join([f"* {b['badge_name']}" for b in t_chunk]),
          inline=False
        )
        chunk_embed.set_footer(
          text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
          icon_url="https://i.imgur.com/GTN4gQG.jpg"
        )
        await trade_channel.send(embed=chunk_embed)

    await self._send_continuum_images_to_channel(trade_channel, continuum_images)

    if player_count == 9:
      await trade_channel.send(f"Hey {active_chair_member.mention}, your table is getting full!")


  async def _cancel_tongo_related_trades(self, user_discord_id, selected_badges):
    # These are all the active or pending trades that involved the user as either the
    # requestee or requestor and include the badges that were added to the tongo pot
    # are thus no longer valid and need to be canceled
    trades_to_cancel = await db_get_related_tongo_badge_trades(user_discord_id, selected_badges)
    if not trades_to_cancel:
      return

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
      user = await get_user(requestor.id)
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
    await ctx.defer(ephemeral=True)
    user_discord_id = ctx.interaction.user.id
    user_member = await self.bot.current_guild.fetch_member(user_discord_id)
    active_tongo = await db_get_active_tongo()

    if not active_tongo:
      await ctx.followup.send(embed=discord.Embed(
          title="No Tongo Game In Progress",
          description="No one is playing Tongo yet!\n\nUse `/tongo venture` to begin a game!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    # Respond to command required
    await ctx.followup.send(embed=discord.Embed(
        title="Index Request Processed!",
        color=discord.Color.dark_purple()
      ), ephemeral=True
    )

    active_tongo_chair_id = int(active_tongo['chair_discord_id'])
    active_chair_member = await self.bot.current_guild.fetch_member(active_tongo_chair_id)

    tongo_players = await db_get_active_tongo_players(active_tongo['id'])
    tongo_player_ids = [int(p['user_discord_id']) for p in tongo_players]
    tongo_player_members = [await self.bot.current_guild.fetch_member(id) for id in tongo_player_ids]

    tongo_pot_badges = await db_get_tongo_pot_badges()
    tongo_pot_chunks = [tongo_pot_badges[i:i + 30] for i in range(0, len(tongo_pot_badges), 30)]

    description=f"Index requested by **{user_member.display_name}**!\n\nDisplaying the status of the current game of Tongo!\n\n"
    if self.auto_confront.next_iteration:
      current_time = datetime.now(timezone.utc)
      remaining_time = current_time - self.auto_confront.next_iteration
      description += f"This Tongo game has {humanize.naturaltime(remaining_time)} left before the game is automatically ended!"

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
      value="\n".join([f"* {b['badge_name']}" for b in tongo_pot_chunks[0]]),
      inline=False
    )
    confirmation_embed.set_image(url="https://i.imgur.com/aWLYGKQ.gif")
    confirmation_embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
      icon_url="https://i.imgur.com/GTN4gQG.jpg"
    )
    continuum_images = await generate_paginated_continuum_images(tongo_pot_badges)
    trade_channel = await self.bot.fetch_channel(get_channel_id("bahrats-bazaar"))
    await trade_channel.send(embed=confirmation_embed)

    if len(tongo_pot_chunks) > 1:
      for t_chunk in tongo_pot_chunks[1:]:
        chunk_embed = discord.Embed(
          title=f"Index requested by **{user_member.display_name}** (Continued)",
          color=discord.Color.dark_purple()
        )
        chunk_embed.add_field(
          name=f"Total Badges In The Great Material Continuum!",
          value="\n".join([f"* {b['badge_name']}" for b in t_chunk]),
          inline=False
        )
        chunk_embed.set_footer(
          text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
          icon_url="https://i.imgur.com/GTN4gQG.jpg"
        )
        await trade_channel.send(embed=chunk_embed)

    await self._send_continuum_images_to_channel(trade_channel, continuum_images)

  async def _send_continuum_images_to_channel(self, trade_channel, continuum_images):
    # We can only attach up to 10 files per message, so them in chunks if needed
    file_chunks = [continuum_images[i:i + 10] for i in range(0, len(continuum_images), 10)]
    for chunk in file_chunks:
      file_number = 1
      for file in chunk:
        await trade_channel.send(
          embed=discord.Embed(
            color=discord.Color.dark_gold()
          ).set_image(url=f"attachment://{file.filename}"),
          file=file
        )
        file_number += 1

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
    await ctx.defer(ephemeral=True)
    user_discord_id = ctx.interaction.user.id
    active_tongo = await db_get_active_tongo()

    if not active_tongo:
      await ctx.followup.send(embed=discord.Embed(
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
        await ctx.followup.send(embed=discord.Embed(
            title="You're Not The Chair!",
            description=f"Only The Chair is allowed to end the Tongo!\n\nThe current Chair is: **{active_chair.display_name}**",
            color=discord.Color.red()
          ),
          ephemeral=True
        )
        return

    tongo_players = await db_get_active_tongo_players(active_tongo['id'])
    tongo_player_ids = [int(p['user_discord_id']) for p in tongo_players]

    if len(tongo_player_ids) < 2:
      await ctx.followup.send(embed=discord.Embed(
          title="You're The Only Player!",
          description="Can't do a Confront when you're the only player in the game! Invite some people!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    # Respond to command required
    await ctx.followup.send(embed=discord.Embed(
        title="Confront Acknowledged!",
        color=discord.Color.dark_purple()
      ), ephemeral=True
    )

    await self._perform_confront(active_tongo, active_chair)

    # Cancel the auto_confront that was started when the venture was fired
    self.auto_confront.cancel()

  #    ___       __           _____          ___              __
  #   / _ |__ __/ /____  ____/ ___/__  ___  / _/______  ___  / /_
  #  / __ / // / __/ _ \/___/ /__/ _ \/ _ \/ _/ __/ _ \/ _ \/ __/
  # /_/ |_\_,_/\__/\___/    \___/\___/_//_/_//_/  \___/_//_/\__/
  @tasks.loop(hours=8)
  async def auto_confront(self):
    if self.first_auto_confront:
      self.first_auto_confront = False
      return

    active_tongo = await db_get_active_tongo()

    if not active_tongo:
      self.auto_confront.cancel()
      return

    tongo_players = await db_get_active_tongo_players(active_tongo['id'])
    active_tongo_chair_id = int(active_tongo['chair_discord_id'])
    active_chair = await bot.current_guild.fetch_member(active_tongo_chair_id)

    # If we never got enough players, end the game and notify the chair
    if len(tongo_players) < 2:
      await db_end_current_tongo(active_tongo['id'])
      # Alert the channel
      trade_channel = await self.bot.fetch_channel(get_channel_id("bahrats-bazaar"))
      await trade_channel.send(embed=discord.Embed(
          title="TONGO! Auto-Canceled!",
          description=f"Whoops, the Tongo game started by {active_chair.display_name} didn't get any other takers and the "
                      "time has run out! Game has been automatically canceled.",
          color=discord.Color.red()
        )
      )
      # Alert the chair
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

    await self._perform_confront(active_tongo, active_chair, True)
    self.auto_confront.cancel()

  async def _perform_confront(self, active_tongo, active_chair, auto_confront=False):
    results = await self._perform_confront_distribution()
    tongo_pot_badges = await db_get_tongo_pot_badges()
    liquidation_result = None

    if auto_confront:
      results_embed = discord.Embed(
        title="TONGO! Game Automatically Ending!",
        description=f"The game started by **{active_chair.display_name}** has run out of time!\n\nEnding the game!",
        color=discord.Color.dark_purple()
      )

      # Grand Nagus Zek's Liquidation
      # Only occurs on auto_confront, 5 or more badges in pot, and 3 or more players
      tongo_players = [r[0] for r in results.items()]
      if len(tongo_pot_badges) >= 5 and len(tongo_players) >= 3:
        # Then there's a 1/3rd chance to Liquidate
        if random.random() < 0.34:
          liquidation_result = await self._determine_liquidation(tongo_players)

    else:
      results_embed = discord.Embed(
        title="TONGO! Complete!",
        description="Distributing Badges from The Great Material Continuum!",
        color=discord.Color.dark_purple()
      )

    if tongo_pot_badges:
      results_embed.add_field(
        name=f"Remaining Badges In The Great Material Continuum!",
        value="\n".join([f"* {b['badge_name']}" for b in tongo_pot_badges]),
        inline=False
      )
    results_embed.set_image(url="https://i.imgur.com/gdpvba5.gif")
    results_embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
      icon_url="https://i.imgur.com/GTN4gQG.jpg"
    )
    trade_channel = await self.bot.fetch_channel(get_channel_id("bahrats-bazaar"))
    channel_message = await trade_channel.send(embed=results_embed)

    for result in results.items():
      player_user_discord_id = result[0]
      player_member = await self.bot.current_guild.fetch_member(player_user_discord_id)
      player_badges_received = [await db_get_badge_info_by_filename(b) for b in list(result[1])]
      player_wishlist = await db_get_user_wishlist_badges(player_user_discord_id)

      if len(player_badges_received) > 0:
        won_badge_filenames = [b['badge_filename'] for b in player_badges_received]
        won_image_id = f"{active_tongo['id']}-won-{result[0]}"
        won_image = await generate_badge_trade_showcase(
          won_badge_filenames,
          won_image_id,
          f"Badges Won By {player_member.display_name}",
          f"{len(player_badges_received)} Badges"
        )
        wishlist_badges_received = [b for b in player_wishlist if b['badge_filename'] in [b['badge_filename'] for b in player_badges_received]]
        wishlist_badge_filenames_received = [b['badge_filename'] for b in wishlist_badges_received]

        description = "\n".join([f"* {b['badge_name']}{' ✨' if b['badge_filename'] in wishlist_badge_filenames_received else ''}" for b in player_badges_received])

        # Check if they got less than 3 back, if so grant them XP based on number missing
        number_of_badges_received = len(player_badges_received)
        if number_of_badges_received < 3:
          no_of_badges_missing = abs(number_of_badges_received - 3)
          xp_to_grant = 110 * no_of_badges_missing
          await increment_user_xp(player_member, xp_to_grant, 'tongo_loss', trade_channel, "Consolation Prize for Tongo Loss")

          xp_granted = xp_to_grant
          if bool(datetime.today().weekday() >= 4):
            xp_granted = xp_to_grant * 2

          description += f"\n\nOops, they got back less than they put in!\nThey've been awarded **{xp_granted}xp** as a consolation prize!"

        player_channel_embed = discord.Embed(
          title=f"{player_member.display_name} Received:",
          description=description,
          color=discord.Color.dark_purple()
        )
        if wishlist_badges_received:
          await db_autolock_badges_by_filenames_if_in_wishlist(player_user_discord_id, wishlist_badge_filenames_received)
          await db_purge_users_wishlist(player_user_discord_id)
          player_channel_embed.set_footer(text="✨ - Indicates a wishlist badge!")
        player_channel_embed.set_image(url=f"attachment://{won_image_id}.png")
        await trade_channel.send(embed=player_channel_embed, file=won_image)

        # Now send message to the player
        if not auto_confront:
          player_message_embed = discord.Embed(
            title=f"TONGO! Confront!",
            description="Your Tongo game has ended! Your winnings are included below, "
                        f"and you can view the full results at: {channel_message.jump_url}",
            color=discord.Color.dark_purple()
          )
        else:
          player_message_embed = discord.Embed(
            title=f"TONGO! Game Automatically Ending!",
            description="Time ran out for your Tongo game and it has automatically ended! Your winnings are included below, "
                        f"and you can view the full results at: {channel_message.jump_url}",
            color=discord.Color.dark_purple()
          )

        player_message_embed.add_field(
          name=f"Badges Acquired",
          value="\n".join([f"* {b['badge_name']}{' ✨' if b['badge_filename'] in [w['badge_filename'] for w in wishlist_badges_received] else ''}" for b in player_badges_received])
        )
        footer_text = "Note you can use /settings to enable or disable these messages."
        if wishlist_badges_received:
          footer_text += "\n✨ - Indicates a wishlist badge!"
        player_message_embed.set_footer(text=footer_text)
        try:
          await player_member.send(embed=player_message_embed)
        except discord.Forbidden as e:
          logger.info(f"Unable to send Tongo completion message to {player_member.display_name}, they have their DMs closed.")
          pass
      else:
        # Grant consolation prize XP for receiving NO badges
        xp_to_grant = 110 * 3
        await increment_user_xp(player_member, xp_to_grant, 'tongo_loss', trade_channel, "Consolation Prize for Tongo Loss")

        xp_granted = xp_to_grant
        if bool(datetime.today().weekday() >= 4):
          xp_granted = xp_to_grant * 2

        player_channel_embed = discord.Embed(
          title=f"{player_member.display_name} Did Not Receive Any Badges...\n\nbut they've been awarded **{xp_granted}xp** as a consolation prize!"
        )
        player_channel_embed.set_image(url="https://i.imgur.com/qZNBAvE.gif")
        await trade_channel.send(embed=player_channel_embed)

        # Now send message to the player
        if not auto_confront:
          player_message_embed = discord.Embed(
            title=f"TONGO! Confront!",
            description="Your Tongo game has ended! Sadly you did not receive any badges...\n\nbut you got some Bonus XP instead!\n\n"
                        f"You can view the full results at: {channel_message.jump_url}",
            color=discord.Color.dark_purple()
          )
        else:
          player_message_embed = discord.Embed(
            title=f"TONGO! Confront!",
            description="Your Tongo game has automatically ended! Sadly you did not receive any badges...\n\nbut you got some Bonus XP instead!\n\n"
                        f"You can view the full results at: {channel_message.jump_url}",
            color=discord.Color.dark_purple()
          )

        player_message_embed.set_image(url="https://i.imgur.com/qZNBAvE.gif")
        player_message_embed.set_footer(text="Note you can use /settings to enable or disable these messages.")
        try:
          await player_member.send(embed=player_message_embed)
        except discord.Forbidden as e:
          logger.info(f"Unable to send Tongo completion message to {player_member.display_name}, they have their DMs closed.")
          pass

    if liquidation_result:
      liquidation_member = await self.bot.current_guild.fetch_member(liquidation_result['player_id'])
      liquidation_reward = liquidation_result['badge_to_grant']

      # Perform the nitty gritty of the liquidation
      # We don't do this earlier because we want to only actually
      # modify the pot _now_ after the tongo distribution has been completed
      for badge in liquidation_result['tongo_badges_to_remove']:
        await db_remove_badge_from_pot(badge['badge_filename'])

      await db_grant_player_badge(liquidation_result['player_id'], liquidation_reward['badge_filename'])

      # Alert the Channel
      liquidation_embed = discord.Embed(
        title="LIQUIDATION!!!",
        description=f"Grand Nagus Zek has stepped in for a Liquidation!\n\n"
                     "The number of badges in The Great Material Continuum was **TOO DAMN HIGH!**\n\n"
                     "By Decree of the Grand Nagus of the Ferengi Alliance, **THREE** Badges from the Continuum have been **LIQUIDATED!**\n\n"
                     f"✨ **{liquidation_member.display_name}** is the *Lucky Liquidation Beneficiary*!!! ✨\n\n"
                     "A deal is a deal... until a better one comes along!\n\n",
        color=discord.Color.gold()
      )
      liquidation_embed.set_image(url="https://i.imgur.com/U9U0doQ.gif")
      liquidation_embed.add_field(
        name=f"{liquidation_member.display_name} receives a random badge they've been coveting...",
        value=f"* {liquidation_reward['badge_name']} ✨",
        inline=False
      )
      liquidation_embed.add_field(
        name="Badges Liquidated from The Great Material Continuum",
        value="\n".join([f"* {b['badge_name']}" for b in liquidation_result['tongo_badges_to_remove']]),
        inline=False
      )
      liquidation_embed.set_footer(
        text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
        icon_url="https://i.imgur.com/GTN4gQG.jpg"
      )
      await trade_channel.send(embed=liquidation_embed)

      # Show the reward embed/image
      endowment_image_id = f"{active_tongo['id']}-liquidation-{liquidation_result['player_id']}"
      endowment_image = await generate_badge_trade_showcase(
        [liquidation_reward['badge_filename']],
        endowment_image_id,
        f"Zek's Endowment For {liquidation_member.display_name}",
        "Greed is Eternal!"
      )
      endowment_embed = discord.Embed(
        title="Liquidation Endowment",
        description=f"As the ✨ *Lucky Liquidation Beneficiary* ✨ **{liquidation_member.display_name}** has been granted a freshly-minted, randomized badge from their wishlist!",
        color=discord.Color.gold()

      )
      endowment_embed.set_image(url=f"attachment://{endowment_image_id}.png")
      await trade_channel.send(embed=endowment_embed, file=endowment_image)

      # Show the badges that were liquidated embed/image
      removal_image_id = f"{active_tongo['id']}-liquidation_badges"
      removal_image = await generate_badge_trade_showcase(
        [b['badge_filename'] for b in liquidation_result['tongo_badges_to_remove']],
        removal_image_id,
        f"Badges Liquidated",
        f"{len(liquidation_result['tongo_badges_to_remove'])} Badges Liquidated"
      )
      removal_embed = discord.Embed(
        title="Badges Liquidated",
        description=f"The following badges have been removed from The Great Material Continuum...",
        color=discord.Color.gold()

      )
      removal_embed.set_image(url=f"attachment://{removal_image_id}.png")
      await trade_channel.send(embed=removal_embed, file=removal_image)

      # Alert the User
      # Notify the player
      player_liquidation_embed = discord.Embed(
          title="LIQUIDATION!",
          description=f"Grand Nagus Zek has decreed a Liquidation of The Great Material Continuum, "
                      "and as the ✨ *Lucky Liquidation Beneficiary* ✨ you have received a randomized badge from your wishlist!\n\n"
                      "**Congratulations!** Greed is Eternal!",
          color=discord.Color.gold()
        )
      player_liquidation_embed.add_field(
        name="You received...",
        value=f"* {liquidation_reward['badge_name']} ✨"
      )
      try:
        await liquidation_member.send(embed=player_liquidation_embed)
      except discord.Forbidden:
        logger.info(f"Unable to send liquidation message to {player_member.display_name}, they have their DMs closed.")
        pass

      # Refresh of Tongo Pot after liquidation has occured
      tongo_pot_badges = await db_get_tongo_pot_badges()

    if tongo_pot_badges:
      continuum_images = await generate_paginated_continuum_images(tongo_pot_badges)
      await self._send_continuum_images_to_channel(trade_channel, continuum_images)

  async def _perform_confront_distribution(self):
    active_tongo = await db_get_active_tongo()
    tongo_players = await db_get_active_tongo_players(active_tongo['id'])
    tongo_player_ids = [int(p['user_discord_id']) for p in tongo_players]
    tongo_pot_badges = await db_get_tongo_pot_badges()
    tongo_pot = [b['badge_filename'] for b in tongo_pot_badges]

    player_distribution = { player_id: set() for player_id in tongo_player_ids }
    player_inventories = {}
    player_wishlists = {}
    for player_id in tongo_player_ids:
      player_inventories[player_id] = [b['badge_filename'] for b in await db_get_user_badges(player_id)]
      player_wishlists[player_id] = [b['badge_filename'] for b in await db_get_user_wishlist_badges(player_id)]

    random.shuffle(tongo_player_ids)
    random.shuffle(tongo_pot)

    # We're going to go round-robin and try to distribute all of the shuffled badges
    turn_index = 0
    players_with_max_badges = set()
    players_with_no_assignable_badges = set()

    while tongo_pot and (len(players_with_max_badges) + len(players_with_no_assignable_badges)) < len(tongo_player_ids):
      current_player_id = tongo_player_ids[turn_index % len(tongo_player_ids)]

      # Skip players who can't receive more badges
      if current_player_id in players_with_max_badges or current_player_id in players_with_no_assignable_badges:
        turn_index += 1
        continue  # Move to the next player

      current_badge = None

      # Loop through the tongo pot to find a valid badge
      for potential_badge in tongo_pot:
        # First, prioritize wishlist badges that the player doesn't already have
        if potential_badge in player_wishlists[current_player_id] and potential_badge not in player_inventories[current_player_id]:
          current_badge = potential_badge
        elif potential_badge not in player_inventories[current_player_id]:
          # If no wishlist match, assign the first badge the player doesn't already have
          current_badge = potential_badge

        # If we found a valid badge, break out of the loop
        if current_badge:
          break

      # If no valid badge is found, mark player as having no assignable badges
      if current_badge is None:
        players_with_no_assignable_badges.add(current_player_id)
        turn_index += 1
        continue  # Move to the next player

      # Assign the valid badge to the player and remove it from the pot
      player_distribution[current_player_id].add(current_badge)
      tongo_pot.remove(current_badge)  # Remove the badge from the main pot

      # Check if the player now has 3 badges
      if len(player_distribution[current_player_id]) >= 3:
        players_with_max_badges.add(current_player_id)

      # Move to the next player
      turn_index += 1

    # Now go through the distribution and actually perform the db handouts and removal from the pot
    for p in player_distribution.items():
      player_id = p[0]
      player_badges = p[1]

      for b in player_badges:
        await db_grant_player_badge(player_id, b)
        await db_remove_badge_from_pot(b)

    # End the current game of tongo
    await db_end_current_tongo(active_tongo['id'])

    return player_distribution

  async def _determine_liquidation(self, tongo_players):
    liquidation_result = None

    tongo_pot_badges = await db_get_tongo_pot_badges()

    # Shuffle players
    players = tongo_players.copy()
    random.shuffle(players)

    # Iterate over players to find one to grant a randomized wishlist badge
    for player in players:
      player_id = int(player)
      # Fetch player's wishlist badges
      wishlist_badges = await db_get_user_wishlist_badges(player_id)
      if wishlist_badges:
        # Fetch player's inventory to ensure they don't already have the badge
        player_inventory = await db_get_user_badges(player_id)

        # Filter wishlist badges the player doesn't own
        wishlist_badges_to_grant = [
          b for b in wishlist_badges if b['badge_filename'] not in [
            b['badge_filename'] for b in player_inventory
          ]
        ]

        if wishlist_badges_to_grant:
          liquidation_result = {}

          # Badge to grant
          random.shuffle(wishlist_badges_to_grant)
          badge_to_grant = wishlist_badges_to_grant[0]
          liquidation_result['player_id'] = player_id
          liquidation_result['badge_to_grant'] = badge_to_grant

          # Badges to remove from pot
          tongo_pot_badges = await db_get_tongo_pot_badges()
          random.shuffle(tongo_pot_badges)
          badges_to_remove = tongo_pot_badges[:3]
          liquidation_result['tongo_badges_to_remove'] = badges_to_remove

          break # Badge granted, exit loop
      # Move to the next player if no wishlist badges to grant

    return liquidation_result

  #   __  ____  _ ___ __  _
  #  / / / / /_(_) (_) /_(_)__ ___
  # / /_/ / __/ / / / __/ / -_|_-<
  # \____/\__/_/_/_/\__/_/\__/___/
  async def _validate_selected_user_badges(self, ctx:discord.ApplicationContext, selected_user_badges):
    if len(selected_user_badges) != 3:
      await ctx.followup.send(embed=discord.Embed(
        title="Invalid Selection",
        description=f"You must own all of the badges you've selected to Risk and they must be Unlocked!",
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

    special_badges = await db_get_special_badges()
    restricted_badges = [b for b in selected_user_badges if b in [b['badge_name'] for b in special_badges]]
    if restricted_badges:
      await ctx.followup.send(embed=discord.Embed(
        title="Invalid Selection",
        description=f"You cannot risk with the following: {','.join(restricted_badges)}!",
        color=discord.Color.red()
      ), ephemeral=True)
      return False

    tongo_pot_badges = await db_get_tongo_pot_badges()
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
async def db_get_active_tongo():
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT * FROM tongo WHERE status = 'active'"
    await query.execute(sql)
    trades = await query.fetchall()
  if trades:
    return trades[0]
  else:
    return None

async def db_get_tongo_pot_badges():
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT * FROM badge_info AS b_i
        JOIN tongo_pot AS t_p
          ON t_p.badge_filename = b_i.badge_filename
          ORDER BY b_i.badge_name ASC
    '''
    await query.execute(sql)
    badges = await query.fetchall()
  return badges

async def db_get_active_tongo_players(tongo_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT * FROM tongo_players AS t_pl
        JOIN tongo AS t
          ON t_pl.tongo_id = t.id
          WHERE t.id = %s
          ORDER BY t_pl.time_created ASC
    '''
    vals = (tongo_id,)
    await query.execute(sql, vals)
    players = await query.fetchall()
  return players

async def db_create_new_tongo(user_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      INSERT INTO tongo (chair_discord_id) VALUES (%s)
    '''
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    result = query.lastrowid
  return result

async def db_add_player_to_tongo(user_discord_id, tongo_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      INSERT INTO tongo_players (user_discord_id, tongo_id) VALUES (%s, %s)
    '''
    vals = (user_discord_id, tongo_id)
    await query.execute(sql, vals)
    result = query.lastrowid
  return result

async def db_add_badges_to_pot(user_discord_id, badges_to_add):
  async with AgimusDB(dictionary=True) as query:
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
    await query.execute(sql, vals)

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
    await query.execute(sql, vals)

async def db_get_related_tongo_badge_trades(user_discord_id, selected_user_badges):
  async with AgimusDB(dictionary=True) as query:
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
      selected_user_badges[0]['badge_filename'], selected_user_badges[1]['badge_filename'], selected_user_badges[2]['badge_filename'],
      selected_user_badges[0]['badge_filename'], selected_user_badges[1]['badge_filename'], selected_user_badges[2]['badge_filename']
    )
    await query.execute(sql, vals)
    trades = await query.fetchall()
  return trades

async def db_grant_player_badge(user_discord_id, badge_filename):
  async with AgimusDB() as query:
    sql = "INSERT INTO badges (user_discord_id, badge_filename) VALUES (%s, %s)"
    vals = (user_discord_id, badge_filename)
    await query.execute(sql, vals)

async def db_remove_badge_from_pot(badge_filename):
  async with AgimusDB() as query:
    sql = "DELETE FROM tongo_pot WHERE badge_filename = %s"
    vals = (badge_filename,)
    await query.execute(sql, vals)

async def db_end_current_tongo(tongo_id):
  async with AgimusDB() as query:
    sql = "UPDATE tongo SET status = 'complete' WHERE id = %s"
    vals = (tongo_id,)
    await query.execute(sql, vals)


# _________                __  .__                           .___
# \_   ___ \  ____   _____/  |_|__| ____  __ __ __ __  _____ |   | _____ _____     ____   ____   ______
# /    \  \/ /  _ \ /    \   __\  |/    \|  |  \  |  \/     \|   |/     \\__  \   / ___\_/ __ \ /  ___/
# \     \___(  <_> )   |  \  | |  |   |  \  |  /  |  /  Y Y  \   |  Y Y  \/ __ \_/ /_/  >  ___/ \___ \
#  \______  /\____/|___|  /__| |__|___|  /____/|____/|__|_|  /___|__|_|  (____  /\___  / \___  >____  >
#         \/            \/             \/                  \/          \/     \//_____/      \/     \/
async def generate_paginated_continuum_images(continuum_badges):
  total_badges = len(continuum_badges)
  max_per_image = 12
  all_pages = [continuum_badges[i:i + max_per_image] for i in range(0, len(continuum_badges), max_per_image)]
  total_pages = len(all_pages)
  badge_images = [
    await generate_continuum_images(
      page,
      page_number + 1,
      total_pages,
      total_badges
    )
    for page_number, page in enumerate(all_pages)
  ]
  return badge_images


@to_thread
def generate_continuum_images(page_badges, page_number, total_pages, total_badges):
  text_wrapper = textwrap.TextWrapper(width=20)
  badge_font = ImageFont.truetype("fonts/context_bold.ttf", 16)
  footer_font = ImageFont.truetype("fonts/luxury.ttf", 42)

  badge_size = 120
  badge_padding = 20
  badge_margin = 40
  badge_vertical_margin = 40
  badge_slot_size = badge_size + (badge_padding * 2) # size of badge slot size (must be square!)
  badges_per_row = 3

  total_rows = math.ceil((len(page_badges) / badges_per_row))

  header_height = 110
  row_height = 200
  footer_height = 115

  base_width = 800
  base_height = (200 * total_rows) + header_height + footer_height

  # Create base image to paste all badges on to
  continuum_base_image = Image.new("RGBA", (base_width, base_height), (0, 0, 0))
  continuum_header_image = Image.open("./images/templates/tongo/continuum_header.png")
  continuum_bg_image = Image.open("./images/templates/tongo/continuum_bg.png")
  continuum_footer_image = Image.open("./images/templates/tongo/continuum_footer.png")

  # Start image with header
  continuum_base_image.paste(continuum_header_image, (0, 0))

  # Stamp BG Rows
  bg_y = header_height
  for i in range(total_rows):
    continuum_base_image.paste(continuum_bg_image, (0, bg_y))
    bg_y += row_height

  # Stamp Footer
  continuum_base_image.paste(continuum_footer_image, (0, bg_y))

  total_text = f"{total_badges} TOTAL"
  page_number_text = ""
  if total_pages > 1:
    page_number_text = f" -- PAGE {'{:02d}'.format(page_number)} OF {'{:02d}'.format(total_pages)}"
  footer_text =f"{total_text}{page_number_text}"

  draw = ImageDraw.Draw(continuum_base_image)
  base_w, base_h = continuum_base_image.size
  # draw.text( (150, base_h-50), total_text, fill="white", font=footer_font, anchor="mm", align="right", stroke_width=2, stroke_fill="#DFBD5C")
  # draw.text( (base_w-200, base_h-50), page_number_text, fill="white", font=footer_font, anchor="mm", align="right", stroke_width=2, stroke_fill="#DFBD5C")
  draw.text( (base_width/2, base_h-50), footer_text, fill="#FCCE67", font=footer_font, anchor="mm", align="center", stroke_width=2, stroke_fill="#B49847")


  # Calcuate centering the row
  half_base_width = int(base_w / 2)

  total_remaining_badges = len(page_badges)
  start_row_badges_length = total_remaining_badges
  if start_row_badges_length >= badges_per_row:
    start_row_badges_length = badges_per_row

  # Get total width of all badges and any margins
  start_row_width = int((badge_slot_size * start_row_badges_length) + (badge_margin * (start_row_badges_length - 1)))
  # Subtract that from the midpoint of the base image
  current_x = int(half_base_width - (start_row_width / 2))
  # Start point for vertical row
  current_y = header_height + int(badge_margin / 2)
  counter = 0

  for badge in page_badges:
    # slot
    s = Image.new("RGBA", (badge_slot_size, badge_slot_size), (0, 0, 0, 0))
    badge_draw = ImageDraw.Draw(s)
    badge_draw.rounded_rectangle( (0, 0, badge_slot_size, badge_slot_size), fill="#000000", outline="#DFBD5C", width=4, radius=32 )

    # badge
    size = (100, 100)
    b_raw = Image.open(f"./images/badges/{badge['badge_filename']}").convert("RGBA")
    b_raw.thumbnail(size, Image.ANTIALIAS)
    b = Image.new('RGBA', size, (255, 255, 255, 0))
    b.paste(
      b_raw, (int((size[0] - b_raw.size[0]) // 2), int((size[1] - b_raw.size[1]) // 2))
    )

    w, h = b.size # badge size
    offset_x = int(badge_slot_size / 2) - (int((w) / 2) + badge_padding) # center badge x
    offset_y = 5

    current_text_wrapper = text_wrapper
    current_badge_font = badge_font
    if len(badge['badge_name']) > 20:
      current_text_wrapper = textwrap.TextWrapper(width=16)
      current_badge_font = ImageFont.truetype("fonts/context_bold.ttf", 14)
    badge_name = current_text_wrapper.wrap(badge['badge_name'])
    wrapped_badge_name = ""
    for i in badge_name[:-1]:
      wrapped_badge_name = wrapped_badge_name + i + "\n"
    wrapped_badge_name += badge_name[-1]
    # add badge to slot
    s.paste(b, (badge_padding+offset_x, offset_y), b)
    badge_draw.text( (int(badge_slot_size/2), 100 + offset_y + 20), f"{wrapped_badge_name}", fill="white", font=current_badge_font, anchor="mm", align="center")

    # add slot to base image
    continuum_base_image.paste(s, (current_x, current_y), s)

    current_x += badge_slot_size + badge_margin
    counter += 1

    if counter % badges_per_row == 0:
      # typewriter sound effects:
      total_remaining_badges = total_remaining_badges - badges_per_row
      current_row_length = total_remaining_badges
      if current_row_length >= badges_per_row:
        current_row_length = badges_per_row

      # Get total width of all row badge slots and any margins
      full_row_width = int((badge_slot_size * current_row_length) + (badge_margin * (current_row_length - 1)))
      # Subtract half the full row width from the midpoint of the base image
      current_x = int(half_base_width - (full_row_width / 2))
      # Drop down a row vertically
      current_y += badge_slot_size + badge_vertical_margin # ka-chunk
      counter = 0 #...

  continuum_image_filename = f"continuum-page-{page_number}-{int(time.time())}.png"

  continuum_base_image.save(f"./images/tongo/{continuum_image_filename}")

  while True:
    time.sleep(0.05)
    if os.path.isfile(f"./images/tongo/{continuum_image_filename}"):
      break

  discord_image = discord.File(fp=f"./images/tongo/{continuum_image_filename}", filename=f"{continuum_image_filename}")
  return discord_image