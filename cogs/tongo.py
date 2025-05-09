from common import *
from handlers.xp import grant_xp

from cogs.trade import get_offered_and_requested_badge_names

from utils.badge_instances import *
from utils.badge_trades import *
from utils.badge_utils import *
from utils.check_channel_access import access_check
from utils.image_utils import generate_badge_trade_images
from utils.prestige import *

from queries.badge_info import *
from queries.badge_instances import *
from queries.tongo import *
from queries.trade import db_cancel_trade
from queries.wishlists import *


f = open("./data/rules_of_acquisition.txt", "r")
data = f.read()
rules_of_acquisition = data.split("\n")
f.close()


TONGO_AUTO_CONFRONT_TIMEOUT = timedelta(hours=6)
MINIMUM_LIQUIDATION_CONTINUUM = 10
MINIMUM_LIQUIDATION_PLAYERS = 3

# -> cogs.tongo

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

  #   _    _    _
  #  | |  (_)__| |_ ___ _ _  ___ _ _ ___
  #  | |__| (_-<  _/ -_) ' \/ -_) '_(_-<
  #  |____|_/__/\__\___|_||_\___|_| /__/
  @commands.Cog.listener()
  async def on_ready(self):
    await self._resume_tongo_if_needed()

  async def _resume_tongo_if_needed(self):
    """
    Called during bot startup to detect if an active Tongo game exists and either:
    - resumes the auto_confront timer with proper timing, or
    - triggers an immediate confront if the timeout has passed.
    """
    active_tongo = await db_get_open_game()
    if not active_tongo:
      return

    try:
      chair_id = int(active_tongo['chair_user_id'])
      chair = await self.bot.current_guild.fetch_member(chair_id)
      zeks_table = await self.bot.fetch_channel(get_channel_id("zeks-table"))
    except Exception as e:
      logger.warning(f"Failed to resume Tongo game: {e}")
      return

    time_created = active_tongo['created_at']
    if time_created.tzinfo is None:
      time_created = time_created.replace(tzinfo=timezone.utc)

    current_time = datetime.now(timezone.utc)
    elapsed = current_time - time_created
    remaining = TONGO_AUTO_CONFRONT_TIMEOUT - elapsed

    if remaining.total_seconds() <= 0:
      downtime_embed = discord.Embed(
        title="DOWNTIME DETECTED! Confronting Tongo...",
        description=f"**Heywaitaminute!!!** Just woke up and noticed that the previous game chaired by **{chair.display_name}** never ended on time!\n\n"
                    "Since the time has elapsed, confronting now! 👉👈",
        color=discord.Color.red()
      )
      downtime_embed.set_image(url="https://i.imgur.com/t5dZu6O.gif")
      downtime_embed.set_footer(
        text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
        icon_url="https://i.imgur.com/GTN4gQG.jpg"
      )
      await zeks_table.send(embed=downtime_embed)
      await self._perform_confront(active_tongo, chair)
    else:
      if self.auto_confront.is_running():
        self.auto_confront.cancel()
      self.auto_confront.change_interval(seconds=remaining.total_seconds())
      self.first_auto_confront = True
      self.auto_confront.start()

      time_left = current_time + remaining
      reboot_embed = discord.Embed(
        title="REBOOT DETECTED! Resuming Tongo...",
        description="We had a game in progress! ***Rude!***\n\n"
                    f"The current game chaired by **{chair.display_name}** has been resumed.\n\n"
                    f"This Tongo game has {humanize.naturaltime(time_left)} left before the game is ended!",
        color=discord.Color.red()
      )
      reboot_embed.set_image(url="https://i.imgur.com/K4hUjh6.gif")
      reboot_embed.set_footer(
        text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
        icon_url="https://i.imgur.com/GTN4gQG.jpg"
      )
      await zeks_table.send(embed=reboot_embed)

  #   _   __         __
  #  | | / /__ ___  / /___ _________
  #  | |/ / -_) _ \/ __/ // / __/ -_)
  #  |___/\__/_//_/\__/\_,_/_/  \__/
  @tongo.command(
    name="venture",
    description="Risk 3 Badges and begin a game of Tongo!"
  )
  @option(
    name="prestige",
    description="Which Prestige Tier to risk?",
    required=True,
    autocomplete=autocomplete_prestige_tiers
  )
  async def venture(self, ctx: discord.ApplicationContext, prestige: str):
    await ctx.defer(ephemeral=True)
    user_id = ctx.author.id
    member = await self.bot.current_guild.fetch_member(user_id)

    if not await is_prestige_valid(ctx, prestige):
      return
    prestige = int(prestige)
    prestige_tier = PRESTIGE_TIERS[prestige]

    existing_game = await db_get_open_game()
    if existing_game:
      if await db_is_user_in_game(existing_game['id'], user_id):
        description = "You've already joined this Tongo game!"
        if user_id == existing_game['chair_user_id']:
          description += f"\n\nPlus you're the one that started it!"
        await ctx.followup.send(embed=discord.Embed(
          title="Already Participating",
          description=description,
          color=discord.Color.red()
        ), ephemeral=True)
        return
      else:
        await ctx.followup.send(embed=discord.Embed(
          title="Tongo Already In Progress",
          description="There's already an ongoing Tongo game!\n\nUse `/tongo risk` to join!",
          color=discord.Color.red()
        ), ephemeral=True)
        return

    badge_instances = await db_get_unlocked_and_unattuned_badge_instances(user_id, prestige=prestige)

    if len(badge_instances) < 3:
      await ctx.followup.send(embed=discord.Embed(
        title="Not Enough Badges",
        description="You need at least 3 eligible badges to begin a Tongo game!",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    continuum_badges = await db_get_full_continuum_badges()
    continuum_badge_ids = [b['badge_info_id'] for b in continuum_badges]
    special_badges = await db_get_special_badge_info()
    special_badge_ids = [b['id'] for b in special_badges]

    all_ids = [b['badge_info_id'] for b in badge_instances]
    if all(id in continuum_badge_ids for id in all_ids):
      if len(all_ids) == 0:
        description = f"You don't possess any (unlocked and unattuned) {prestige_tier} Badges!"
      else:
        description = f"All of the Badges in your {prestige_tier} collection are already in the Continuum!"

      embed = discord.Embed(
        title="No Badges Viable For Random Selection!",
        description=description,
        color=discord.Color.red()
      )
      embed.set_footer(text="Try unlocking some others!")
      await ctx.followup.send(embed=embed, ephemeral=True)
      return

    eligible = [b for b in badge_instances if b['badge_info_id'] not in continuum_badge_ids and b['badge_info_id'] not in special_badge_ids]

    if len(eligible) < 3:
      embed = discord.Embed(
        title=f"Not Enough Viable {prestige_tier} Badges Available!",
        description=f"You only have {len(eligible)} available to randomly select — you need at least 3!",
        color=discord.Color.red()
      )
      embed.set_footer(text="Try unlocking some others!")
      await ctx.followup.send(embed=embed, ephemeral=True)
      return

    selected = random.sample(eligible, 3)

    game_id = await db_create_tongo_game(user_id)
    await db_add_game_player(game_id, user_id)

    for instance in selected:
      await throw_badge_into_continuum(instance, user_id)

    await ctx.followup.send(embed=discord.Embed(
      title="Venture Acknowledged!",
      description="You've started a new game of Tongo.",
      color=discord.Color.dark_purple()
    ), ephemeral=True)

    venture_badges = [await db_get_badge_info_by_id(b['badge_info_id']) for b in selected]

    embed = discord.Embed(
      title="TONGO! Badges Ventured!",
      description=f"**{member.display_name}** has begun a new game of Tongo!\n\n"
                  f"They threw in 3 {prestige_tier} badges from their unlocked inventory into the Great Material Continuum.\n\n"
                  "The wheel is spinning, the game will end in 6 hours, and the badges will be distributed!",
      color=discord.Color.dark_purple()
    )
    embed.add_field(
      name=f"{prestige_tier} Badges Ventured By {member.display_name}",
      value="\n".join([f"* {b['badge_name']}" for b in venture_badges]),
      inline=False
    )
    embed.set_image(url="https://i.imgur.com/tRi1vYq.gif")
    embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
      icon_url="https://i.imgur.com/GTN4gQG.jpg"
    )

    zeks_table = await self.bot.fetch_channel(get_channel_id("zeks-table"))
    await zeks_table.send(embed=embed)

    updated_continuum_badges = await db_get_full_continuum_badges()
    images = await generate_paginated_continuum_images(updated_continuum_badges)
    await send_continuum_images_to_channel(zeks_table, images)

    # Autoconfront
    if self.auto_confront.is_running():
      self.auto_confront.cancel()

    self.auto_confront.change_interval(seconds=TONGO_AUTO_CONFRONT_TIMEOUT.total_seconds())
    self.first_auto_confront = True
    self.auto_confront.start()

  #    ___  _     __
  #   / _ \(_)__ / /__
  #  / , _/ (_-</  '_/
  # /_/|_/_/___/_/\_\
  @tongo.command(
    name="risk",
    description="Join an ongoing game of Tongo by throwing 3 badges into the Continuum!"
  )
  @option(
    name="prestige",
    description="Which Prestige Tier to risk?",
    required=True,
    autocomplete=autocomplete_prestige_tiers
  )
  async def risk(self, ctx: discord.ApplicationContext, prestige: str):
    await ctx.defer(ephemeral=True)
    user_id = ctx.author.id
    member = await self.bot.current_guild.fetch_member(user_id)

    if not await is_prestige_valid(ctx, prestige):
      return
    prestige = int(prestige)
    prestige_tier = PRESTIGE_TIERS[prestige]

    game = await db_get_open_game()
    if not game:
      await ctx.followup.send(embed=discord.Embed(
        title="No Ongoing Tongo Game",
        description="You can't risk badges unless a game is already in progress!\n\nUse `/tongo venture` to start one.",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    if await db_is_user_in_game(game['id'], user_id):
      description = "You've already joined this Tongo game!"
      if user_id == game['chair_user_id']:
        description += f"\n\nPlus you're the one that started it!"
      await ctx.followup.send(embed=discord.Embed(
        title="Already Participating",
        description=description,
        color=discord.Color.red()
      ), ephemeral=True)
      return

    badge_instances = await db_get_unlocked_and_unattuned_badge_instances(user_id, prestige=prestige)

    if len(badge_instances) < 3:
      await ctx.followup.send(embed=discord.Embed(
        title=f"Not Enough {prestige_tier} Badges",
        description="You need at least 3 eligible badges to join Tongo!",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    continuum_badge_info_ids = await db_get_continuum_badge_info_ids()
    special_badge_ids = [b['id'] for b in await db_get_special_badge_info()]

    eligible = [b for b in badge_instances if b['badge_info_id'] not in continuum_badge_info_ids and b['badge_info_id'] not in special_badge_ids]

    if len(eligible) < 3:
      await ctx.followup.send(embed=discord.Embed(
        title=f"Not Enough {prestige_tier} Viable Badges",
        description=f"You only have {len(eligible)} badges eligible to throw in — you need at least 3!",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    selected = random.sample(eligible, 3)
    await db_add_game_player(game['id'], user_id)

    for instance in selected:
      await throw_badge_into_continuum(instance, user_id)

    await ctx.followup.send(embed=discord.Embed(
      title="Risk Acknowledged!",
      color=discord.Color.dark_purple()
    ), ephemeral=True)

    risked_badges = [await db_get_badge_info_by_id(b['badge_info_id']) for b in selected]

    # Get player and continuum state for embeds
    player_ids = await db_get_all_game_player_ids(game['id'])
    player_members = [await self.bot.current_guild.fetch_member(pid) for pid in player_ids]
    all_badges = await db_get_full_continuum_badges()

    # Chunk the continuum into 30s
    continuum_chunks = [all_badges[i:i + 30] for i in range(0, len(all_badges), 30)]
    player_count = len(player_members)

    # Embed flavor
    description = f"### **{member.display_name}** has joined the table!\n\nA new challenger appears! Player {player_count} has entered the game with 3 {prestige_tier} badges from their unlocked inventory!"
    if self.auto_confront.next_iteration:
      description += f"\n\nThis Tongo game will Confront {humanize.naturaltime(self.auto_confront.next_iteration)}."

    embed = discord.Embed(
      title=f"TONGO! {prestige_tier} Badges Risked!",
      description=description,
      color=discord.Color.dark_purple()
    )
    embed.add_field(
      name=f"{prestige_tier} Badges Risked By {member.display_name}",
      value="\n".join([f"* {b['badge_name']}" for b in risked_badges]),
      inline=False
    )
    embed.add_field(
      name=f"Current Players ({player_count})",
      value="\n".join([f"* {m.display_name}" for m in player_members]),
      inline=False
    )
    embed.add_field(
      name=f"Total Badges In The Great Material Continuum!",
      value="\n".join([f"* {b['badge_name']}" for b in continuum_chunks[0]]),
      inline=False
    )
    embed.set_image(url="https://i.imgur.com/zEvF7uO.gif")
    embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
      icon_url="https://i.imgur.com/GTN4gQG.jpg"
    )

    zeks_table = await self.bot.fetch_channel(get_channel_id("zeks-table"))
    await zeks_table.send(embed=embed)

    for chunk in continuum_chunks[1:]:
      chunk_embed = discord.Embed(
        title=f"TONGO! Badges risked by **{member.display_name}** (Continued)!",
        color=discord.Color.dark_purple()
      )
      chunk_embed.add_field(
        name="Total Badges In The Great Material Continuum!",
        value="\n".join([f"* {b['badge_name']}" for b in chunk]),
        inline=False
      )
      chunk_embed.set_footer(
        text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
        icon_url="https://i.imgur.com/GTN4gQG.jpg"
      )
      await zeks_table.send(embed=chunk_embed)

    continuum_images = await generate_paginated_continuum_images(all_badges)
    await send_continuum_images_to_channel(zeks_table, continuum_images)

    if player_count == 9:
      chair = await self.bot.current_guild.fetch_member(game['chair_user_id'])
      await zeks_table.send(f"Hey {chair.mention}, your table is getting full!")


  async def _cancel_tongo_related_trades(self, user_discord_id, selected_badges: list[dict]):
    trades_to_cancel = await db_get_related_tongo_badge_trades(user_discord_id, selected_badges)
    if not trades_to_cancel:
      return

    for trade in trades_to_cancel:
      await db_cancel_trade(trade)

      requestor = await self.bot.current_guild.fetch_member(trade['requestor_id'])
      requestee = await self.bot.current_guild.fetch_member(trade['requestee_id'])

      offered_badge_names, requested_badge_names = await get_offered_and_requested_badge_names(trade)

      # Notify requestee
      requestee_user = await get_user(requestee.id)
      if trade['status'] == 'active' and requestee_user["receive_notifications"]:
        try:
          embed = discord.Embed(
            title="Trade Canceled",
            description=f"Just a heads up! Your USS Hood Badge Trade initiated by **{requestor.display_name}** was canceled because one or more of the badges involved were added to The Great Material Continuum!",
            color=discord.Color.purple()
          )
          embed.add_field(name=f"Offered by {requestor.display_name}", value=offered_badge_names)
          embed.add_field(name=f"Requested from {requestee.display_name}", value=requested_badge_names)
          embed.set_footer(text="Note: You can use /settings to enable or disable these messages.")
          await requestee.send(embed=embed)
        except discord.Forbidden:
          logger.info(f"Unable to send trade cancellation message to {requestee.display_name}, they have their DMs closed.")

      # Notify requestor
      requestor_user = await get_user(requestor.id)
      if requestor_user["receive_notifications"]:
        try:
          embed = discord.Embed(
            title="Trade Canceled",
            description=f"Just a heads up! Your USS Hood Badge Trade requested from **{requestee.display_name}** was canceled because one or more of the badges involved were added to The Great Material Continuum!",
            color=discord.Color.purple()
          )
          embed.add_field(name=f"Offered by {requestor.display_name}", value=offered_badge_names)
          embed.add_field(name=f"Requested from {requestee.display_name}", value=requested_badge_names)
          embed.set_footer(text="Note: You can use /settings to enable or disable these messages.")
          await requestor.send(embed=embed)
        except discord.Forbidden:
          logger.info(f"Unable to send trade cancellation message to {requestor.display_name}, they have their DMs closed.")


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
    user_discord_id = ctx.user.id
    user_member = await self.bot.current_guild.fetch_member(user_discord_id)

    active_tongo = await db_get_open_game()
    if not active_tongo:
      await ctx.followup.send(embed=discord.Embed(
        title="No Tongo Game In Progress",
        description="No one is playing Tongo yet!\n\nUse `/tongo venture` to begin a game!",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    await ctx.followup.send(embed=discord.Embed(
      title="Index Request Processed!",
      color=discord.Color.dark_purple()
    ), ephemeral=True)

    active_tongo_chair_id = int(active_tongo['chair_user_id'])
    active_chair_member = await self.bot.current_guild.fetch_member(active_tongo_chair_id)

    # Get current players
    tongo_players = await db_get_players_for_game(active_tongo['id'])
    tongo_player_ids = [int(p['user_discord_id']) for p in tongo_players]
    tongo_player_members = [await self.bot.current_guild.fetch_member(id) for id in tongo_player_ids]

    # Get current continuum (pot)
    tongo_pot_badges = await db_get_full_continuum_badges()
    tongo_pot_chunks = [tongo_pot_badges[i:i + 30] for i in range(0, len(tongo_pot_badges), 30)]

    description = f"Index requested by **{user_member.display_name}**!\n\nDisplaying the status of the current game of Tongo!"
    if self.auto_confront.next_iteration:
      description += f"\n\nThis Tongo game will Confront {humanize.naturaltime(self.auto_confront.next_iteration)}."

    # First embed
    confirmation_embed = discord.Embed(
      title="TONGO! Call For Index!",
      description=description,
      color=discord.Color.dark_purple()
    )
    confirmation_embed.add_field(
      name="Tongo Chair",
      value=f"* {active_chair_member.display_name}",
      inline=False
    )
    confirmation_embed.add_field(
      name="Current Players",
      value="\n".join([f"* {m.display_name}" for m in tongo_player_members]),
      inline=False
    )
    confirmation_embed.add_field(
      name="Total Badges In The Great Material Continuum!",
      value="\n".join([f"* {b['badge_name']}" for b in tongo_pot_chunks[0]]) if tongo_pot_chunks else "* (empty)",
      inline=False
    )
    confirmation_embed.set_image(url="https://i.imgur.com/aWLYGKQ.gif")
    confirmation_embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
      icon_url="https://i.imgur.com/GTN4gQG.jpg"
    )

    zeks_table = await self.bot.fetch_channel(get_channel_id("zeks-table"))
    await zeks_table.send(embed=confirmation_embed)

    # Continuation embeds if needed
    if len(tongo_pot_chunks) > 1:
      for t_chunk in tongo_pot_chunks[1:]:
        chunk_embed = discord.Embed(
          title=f"Index requested by **{user_member.display_name}** (Continued)",
          color=discord.Color.dark_purple()
        )
        chunk_embed.add_field(
          name="Total Badges In The Great Material Continuum!",
          value="\n".join([f"* {b['badge_name']}" for b in t_chunk]),
          inline=False
        )
        chunk_embed.set_footer(
          text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
          icon_url="https://i.imgur.com/GTN4gQG.jpg"
        )
        await zeks_table.send(embed=chunk_embed)

    # Continuum image display
    continuum_images = await generate_paginated_continuum_images(tongo_pot_badges)
    await send_continuum_images_to_channel(zeks_table, continuum_images)

  #    ___       __           _____          ___              __
  #   / _ |__ __/ /____  ____/ ___/__  ___  / _/______  ___  / /_
  #  / __ / // / __/ _ \/___/ /__/ _ \/ _ \/ _/ __/ _ \/ _ \/ __/
  # /_/ |_\_,_/\__/\___/    \___/\___/_//_/_//_/  \___/_//_/\__/
  @tasks.loop(hours=6)
  async def auto_confront(self):
    if self.first_auto_confront:
      self.first_auto_confront = False
      return

    active_tongo = await db_get_open_game()

    if not active_tongo:
      self.auto_confront.cancel()
      return

    tongo_players = await db_get_players_for_game(active_tongo['id'])
    active_tongo_chair_id = int(active_tongo['chair_user_id'])
    active_chair = await self.bot.current_guild.fetch_member(active_tongo_chair_id)

    # If we never got enough players, end the game and notify the chair
    if len(tongo_players) < 2:
      await db_update_game_status(active_tongo['id'], 'cancelled')
      # Alert the channel
      zeks_table = await self.bot.fetch_channel(get_channel_id("zeks-table"))
      await zeks_table.send(embed=discord.Embed(
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
    await db_update_game_status(active_tongo['id'], 'ended')
    self.auto_confront.cancel()


  async def _perform_confront(self, active_tongo, active_chair):
    player_distribution = await self._execute_confront_distribution(active_tongo['id'])
    player_ids = list(player_distribution.keys())

    remaining_badges = await db_get_full_continuum_badges()

    # Handle potential liquidation
    liquidation_result = await self._handle_liquidation(active_tongo['id'], remaining_badges, player_ids)

    # Build and send results embed
    results_embed = await build_confront_results_embed(active_chair, remaining_badges)
    zeks_table = await self.bot.fetch_channel(get_channel_id("zeks-table"))
    channel_message = await zeks_table.send(embed=results_embed)

    # Show per-player rewards
    for user_id, badge_instance_ids in player_distribution.items():
      member = await self.bot.current_guild.fetch_member(user_id)

      # Wishlist Determination
      echelon_progress = await db_get_echelon_progress(user_id)
      prestige = echelon_progress['current_prestige_tier'] if echelon_progress else 0
      active_wants = await db_get_active_wants(user_id, prestige)
      wanted_filenames = set(b['badge_filename'] for b in active_wants)

      if badge_instance_ids:
        badges_received = [
          await db_get_badge_info_by_instance_id(instance_id)
          for instance_id in badge_instance_ids
        ]
        wishlist_filenames_received = [b['badge_filename'] for b in badges_received if b['badge_filename'] in wanted_filenames]

        received_image, received_image_url = await generate_badge_trade_images(
          badges_received,
          f"Badges Won By {member.display_name}",
          f"{len(badges_received)} Badges"
        )

        xp_awarded = 0
        if len(badge_instance_ids) < 3:
          xp_awarded = 110 * (3 - len(badge_instance_ids))
          if datetime.today().weekday() >= 4:
            xp_awarded *= 2
          await grant_xp(member.id, xp_awarded, 'tongo_loss', zeks_table, "Consolation Prize for Tongo Loss")

        player_embed = await build_confront_player_embed(member, badges_received, wishlist_filenames_received, xp_awarded)
        player_embed.set_image(url=received_image_url)
        await zeks_table.send(embed=player_embed, file=received_image)

        dm_embed = build_confront_dm_embed(member, badges_received, wishlist_filenames_received, channel_message.jump_url, xp_awarded)
        try:
          await member.send(embed=dm_embed)
        except discord.Forbidden:
          logger.info(f"Unable to DM {member.display_name} — DMs closed.")
      else:
        xp_awarded = 110 * 3
        if datetime.today().weekday() >= 4:
          xp_awarded *= 2
        await grant_xp(member.id, xp_awarded, 'tongo_loss', zeks_table, "Consolation Prize for Tongo Loss")

        channel_embed = build_confront_no_rewards_embed(member, xp_awarded)
        await zeks_table.send(embed=channel_embed)

        dm_embed = build_confront_dm_embed(member, [], [], channel_message.jump_url, xp_awarded)
        try:
          await member.send(embed=dm_embed)
        except discord.Forbidden:
          logger.info(f"Unable to DM {member.display_name} — DMs closed.")

    # If liquidation occurred, display the results
    if liquidation_result:
      member = await self.bot.current_guild.fetch_member(liquidation_result['player_id'])
      reward = liquidation_result['badge_to_grant']
      removed = liquidation_result['tongo_badges_to_remove']

      # Main embed
      await zeks_table.send(embed=build_liquidation_embed(member, reward, removed))

      # Endowment image
      reward_image, reward_image_url = await generate_badge_trade_images(reward, f"Zek's Endowment For {member.display_name}", "Greed is Eternal!")
      await zeks_table.send(embed=build_liquidation_endowment_embed(member, reward_image_url), file=reward_image)

      # Liquidated image
      removal_image, removal_image_url = await generate_badge_trade_images(removed, "Badges Liquidated", f"{len(removed)} Badges Liquidated")
      await zeks_table.send(embed=build_liquidation_removal_embed(removed, removal_image_url), file=removal_image)

      # DM
      try:
        await member.send(embed=build_liquidation_dm_embed(member, reward))
      except discord.Forbidden:
        logger.info(f"Unable to DM {member.display_name} about liquidation — DMs closed.")

    # Refresh final continuum display
    updated = await db_get_full_continuum_badges()
    if updated:
      images = await generate_paginated_continuum_images(updated)
      await send_continuum_images_to_channel(zeks_table, images)


  async def _execute_confront_distribution(self, game_id: int) -> dict[int, set[int]]:
    players = await db_get_players_for_game(game_id)
    player_ids = [int(p['user_discord_id']) for p in players]

    continuum_records = await db_get_full_continuum_badges()
    if not continuum_records:
      return {}

    continuum_distribution: set[int] = set()
    player_distribution: dict[int, set[int]] = {pid: set() for pid in player_ids}
    player_inventories: dict[int, set[int]] = {}
    player_wishlists: dict[int, set[int]] = {}
    player_prestige: dict[int, int] = {}

    # Build inventory, active wants (wishlist), and prestige data
    for player_id in player_ids:
      # Inventory info_ids
      inventory = await db_get_owned_badge_filenames(player_id, prestige=prestige)
      owned_info_ids = set()
      for item in inventory:
        info = await db_get_badge_info_by_filename(item['badge_filename'])
        if info:
          owned_info_ids.add(info['id'])
      player_inventories[player_id] = owned_info_ids

      # Prestige, needed for both filtering and wishlist query
      echelon_progress = await db_get_echelon_progress(player_id)
      prestige = echelon_progress['current_prestige_tier'] if echelon_progress else 0
      player_prestige[player_id] = prestige

      # Wishlist 'active wants' only (not owned at current prestige)
      active_wants = await db_get_active_wants(player_id, prestige)
      wishlist_info_ids = set(b['badge_info_id'] for b in active_wants)
      player_wishlists[player_id] = wishlist_info_ids

    # Shuffle for fairness
    random.shuffle(player_ids)
    random.shuffle(continuum_records)

    turn_index = 0
    players_with_max_badges = set()
    players_with_no_assignable_badges = set()

    while continuum_records and (len(players_with_max_badges) + len(players_with_no_assignable_badges)) < len(player_ids):
      current_player = player_ids[turn_index % len(player_ids)]
      prestige_limit = player_prestige[current_player]

      if current_player in players_with_max_badges or current_player in players_with_no_assignable_badges:
        turn_index += 1
        continue

      selected_badge = None
      for badge in continuum_records:
        if badge['prestige_level'] > prestige_limit:
          continue  # Skip if above player's tier

        info_id = badge['badge_info_id']
        inventory = player_inventories[current_player]
        wishlist = player_wishlists[current_player]

        if info_id in wishlist and info_id not in inventory:
          selected_badge = badge
          break
        elif info_id not in inventory:
          selected_badge = badge
          break

      if not selected_badge:
        players_with_no_assignable_badges.add(current_player)
        turn_index += 1
        continue

      instance_id = selected_badge['source_instance_id']
      player_distribution[current_player].add(instance_id)
      continuum_distribution.add(instance_id)
      continuum_records.remove(selected_badge)

      if len(player_distribution[current_player]) >= 3:
        players_with_max_badges.add(current_player)

      turn_index += 1

    # Assign badges and record rewards
    for player_user_id, reward_badge_instances in player_distribution.items():
      for instance_id in reward_badge_instances:
        await transfer_badge_instance(instance_id, player_user_id, event_type='tongo_reward')
        await db_add_game_reward(game_id, player_user_id, instance_id)

    for continuum_instance_id in continuum_distribution:
      await db_remove_from_continuum(continuum_instance_id)

    return player_distribution


  async def _handle_liquidation(self, game_id: int, tongo_continuum: list[dict], player_ids: list[int]) -> Optional[dict]:
    if len(tongo_continuum) < MINIMUM_LIQUIDATION_CONTINUUM or len(player_ids) < MINIMUM_LIQUIDATION_PLAYERS:
      return None

    if random.randint(0, 1) != 1:
      return None

    liquidation_result = await self._determine_liquidation(tongo_continuum, player_ids)
    if not liquidation_result:
      return None

    # Liquidate the selected badges
    for badge in liquidation_result['tongo_badges_to_remove']:
      await db_remove_from_continuum(badge['source_instance_id'])
      await liquidate_badge_instance(badge['source_instance_id'])

    badge_info_id = liquidation_result['badge_to_grant']['id']
    beneficiary_id = liquidation_result['beneficiary_id']

    # Create a new instance using utility helper that tracks origin reason
    reward_instance = await create_new_badge_instance(beneficiary_id, badge_info_id, event_type='liquidation_endowment')
    if not reward_instance:
      return None

    await db_add_game_reward(game_id, beneficiary_id, reward_instance['id'])
    # XXX - Handle autolocking in transfer helper?
    # await db_autolock_badges_by_filenames_if_in_wishlist(beneficiary_id, [reward_instance['badge_filename']])
    # await db_purge_users_wishlist(beneficiary_id)

    liquidation_result['reward_instance_id'] = reward_instance['badge_instance_id']
    return liquidation_result


  async def _determine_liquidation(self, continuum: list[dict], tongo_players: list[int]) -> Optional[dict]:
    players = tongo_players.copy()
    random.shuffle(players)

    for player_id in players:
      echelon_progress = await db_get_echelon_progress(player_id)
      prestige = echelon_progress['current_prestige_tier'] if echelon_progress else 0
      active_wants = await db_get_active_wants(player_id, prestige)

      inventory_filenames = set(b['badge_filename'] for b in await db_get_owned_badge_filenames(player_id, prestige=prestige))
      wishlist_to_grant = [b for b in active_wants if b['badge_filename'] not in inventory_filenames]

      if not wishlist_to_grant:
        continue

      random.shuffle(wishlist_to_grant)
      badge_to_grant = wishlist_to_grant[0]

      # Just pick 3 random continuum badges to liquidate
      available_badges = continuum.copy()
      random.shuffle(available_badges)
      badges_to_remove = available_badges[:3]

      liquidation_result = {
        'beneficiary_id': player_id,
        'badge_to_grant': badge_to_grant,
        'tongo_badges_to_remove': badges_to_remove
      }

      return liquidation_result

    return None


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

    special_badges = await db_get_special_badge_info()
    restricted_badges = [b for b in selected_user_badges if b in [b['badge_name'] for b in special_badges]]
    if restricted_badges:
      await ctx.followup.send(embed=discord.Embed(
        title="Invalid Selection",
        description=f"You cannot risk with the following: {','.join(restricted_badges)}!",
        color=discord.Color.red()
      ), ephemeral=True)
      return False

    continuum_badges = await db_get_full_continuum_badges()
    existing_pot_badges = [b for b in selected_user_badges if b in [b['badge_info_id'] for b in continuum_badges]]
    if existing_pot_badges:
      await ctx.followup.send(embed=discord.Embed(
        title="Invalid Selection",
        description=f"The following badges are already in The Great Material Continuum: {','.join(existing_pot_badges)}!",
        color=discord.Color.red()
      ), ephemeral=True)
      return False

    return True


#
# UTILS
#

async def throw_badge_into_continuum(instance, user_id):
  """
  Utility to place a badge into the continuum and, importantly, revoke the current user's ownership
  """
  await db_add_to_continuum(instance['badge_info_id'], instance['badge_instance_id'], user_id)
  await transfer_badge_instance(instance['badge_instance_id'], None, 'tongo_risk')


async def send_continuum_images_to_channel(trade_channel, continuum_images):
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


# Messaging Utils
async def build_confront_results_embed(active_chair: discord.Member, remaining_badges: list[dict]) -> discord.Embed:
  title = "TONGO! Complete!"
  description= "Distributing Badges from The Great Material Continuum!"

  embed = discord.Embed(
    title=title,
    description=description,
    color=discord.Color.dark_purple()
  )

  if remaining_badges:
    embed.add_field(
      name="Remaining Badges In The Great Material Continuum!",
      value="\n".join([f"* {b['badge_name']}" for b in remaining_badges]),
      inline=False
    )

  embed.set_image(url="https://i.imgur.com/gdpvba5.gif")
  embed.set_footer(
    text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
    icon_url="https://i.imgur.com/GTN4gQG.jpg"
  )

  return embed

async def build_confront_player_embed(member: discord.Member, badge_infos: list[dict], wishlist_badge_filenames: list[str], xp_awarded: int = 0) -> discord.Embed:
  if xp_awarded:
    description = f"\n\nOops, sorry {member.mention}... they got back less than they put in!\n\nOn the bright side they've been awarded **{xp_awarded}xp** as a consolation prize!"
  else:
    description = "\n".join([
      f"* {b['badge_name']}{' ✨' if b['badge_filename'] in wishlist_badge_filenames else ''}"
      for b in badge_infos
    ])

  embed = discord.Embed(
    title=f"{member.display_name}'s Results:",
    description=description,
    color=discord.Color.dark_purple()
  )
  if wishlist_badge_filenames:
    embed.set_footer(text="✨ - Indicates a wishlist badge!")

  return embed


def build_confront_dm_embed(member: discord.Member, badge_infos: list[dict], wishlist_badge_filenames: list[str], jump_url: str, xp_awarded: int = 0) -> discord.Embed:
  title = "TONGO! Confront!"
  description= f"Heya {member.display_name}! Your Tongo game has ended!"

  if xp_awarded:
    description+= f"\n\nOops, you received fewer than 3 badges — so you've been awarded **{xp_awarded}xp** as a consolation prize, but can view the full game results at: {jump_url}"
  else:
    description+= f"\n\nYour winnings are included below, and you can view the full game results at: {jump_url}"

  embed = discord.Embed(
    title=title,
    description=description,
    color=discord.Color.dark_purple()
  )

  if badge_infos:
    embed.add_field(
      name="Badges Acquired",
      value="\n".join([
        f"* {b['badge_name']}{' ✨' if b['badge_filename'] in wishlist_badge_filenames else ''}"
        for b in badge_infos
      ])
    )
  else:
    embed.set_image(url="https://i.imgur.com/qZNBAvE.gif")

  footer_text = "Note you can use /settings to enable or disable these messages."
  if wishlist_badge_filenames:
    footer_text += "\n✨ - Indicates a wishlist badge!"
  embed.set_footer(text=footer_text)

  return embed


def build_confront_no_rewards_embed(member: discord.Member, xp_awarded: int) -> discord.Embed:
  embed = discord.Embed(
    title=f"{member.display_name} did not receive any badges...",
    description=f"but they've been awarded **{xp_awarded}xp** as a consolation prize!",
    color=discord.Color.dark_purple()
  )
  embed.set_image(url="https://i.imgur.com/qZNBAvE.gif")
  return embed


def build_liquidation_embed(member: discord.Member, reward_badge: dict, removed_badges: list[dict]) -> discord.Embed:
  embed = discord.Embed(
    title="LIQUIDATION!!!",
    description=(
      f"Grand Nagus Zek has stepped in for a Liquidation!\n\n"
      "The number of badges in The Great Material Continuum was **TOO DAMN HIGH!**\n\n"
      "By Decree of the Grand Nagus of the Ferengi Alliance, **THREE** Badges from the Continuum have been **LIQUIDATED!**\n\n"
      f"✨ **{member.display_name}** is the *Lucky Liquidation Beneficiary*!!! ✨\n\n"
      "A deal is a deal... until a better one comes along!"
    ),
    color=discord.Color.gold()
  )

  embed.set_image(url="https://i.imgur.com/U9U0doQ.gif")

  embed.add_field(
    name=f"{member.display_name} receives a random badge they've been coveting...",
    value=f"* {reward_badge['badge_name']} ✨",
    inline=False
  )

  embed.add_field(
    name="Badges Liquidated from The Great Material Continuum",
    value="\n".join([f"* {b['badge_name']}" for b in removed_badges]),
    inline=False
  )

  embed.set_footer(
    text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
    icon_url="https://i.imgur.com/GTN4gQG.jpg"
  )

  return embed

def build_liquidation_dm_embed(member: discord.Member, reward_badge: dict) -> discord.Embed:
  embed = discord.Embed(
    title="LIQUIDATION!",
    description=(
      f"Heya {member.display_name}, Grand Nagus Zek has decreed a Liquidation of The Great Material Continuum, "
      f"and as the ✨ *Lucky Liquidation Beneficiary* ✨ you have received a randomized badge from your wishlist!\n\n"
      "**Congratulations!** Greed is Eternal!"
    ),
    color=discord.Color.gold()
  )

  embed.add_field(
    name="You received...",
    value=f"* {reward_badge['badge_name']} ✨"
  )

  return embed


def build_liquidation_endowment_embed(member: discord.Member, reward_image_url) -> discord.Embed:
  embed = discord.Embed(
    title="Liquidation Endowment",
    description=(
      f"As the ✨ *Lucky Liquidation Beneficiary* ✨ **{member.display_name}** has been granted a freshly-minted, randomized badge from their wishlist!"
    ),
    color=discord.Color.gold()
  )
  embed.set_image(url=reward_image_url)
  return embed


def build_liquidation_removal_embed(badges: list[dict], removal_image_url) -> discord.Embed:
  embed = discord.Embed(
    title="Badges Liquidated",
    description="The following badges have been removed from The Great Material Continuum...",
    color=discord.Color.gold()
  )
  embed.set_image(url=removal_image_url)
  return embed


# ________                      .__
# \_____  \  __ __   ___________|__| ____   ______
#  /  / \  \|  |  \_/ __ \_  __ \  |/ __ \ /  ___/
# /   \_/.  \  |  /\  ___/|  | \/  \  ___/ \___ \
# \_____\ \_/____/  \___  >__|  |__|\___  >____  >
#        \__>           \/              \/     \/

async def db_get_related_tongo_badge_trades(user_discord_id, selected_user_badges):
  badge_filenames = [b['badge_filename'] for b in selected_user_badges]

  placeholders = ', '.join(['%s'] * len(badge_filenames))

  async with AgimusDB(dictionary=True) as query:
    sql = f'''
      SELECT t.*

      FROM badge_instance_trades AS t
      LEFT JOIN trade_offered_badge_instances AS to_i ON t.id = to_i.trade_id
      LEFT JOIN trade_requested_badge_instances AS tr_i ON t.id = tr_i.trade_id

      JOIN badge_instances AS b1 ON to_i.badge_instance_id = b1.id
      JOIN badge_instances AS b2 ON tr_i.badge_instance_id = b2.id

      JOIN badge_info AS bi1 ON b1.badge_info_id = bi1.id
      JOIN badge_info AS bi2 ON b2.badge_info_id = bi2.id

      WHERE t.status IN ('pending', 'active')
        AND (t.requestor_id = %s OR t.requestee_id = %s)
        AND (
          bi1.badge_filename IN ({placeholders})
          OR bi2.badge_filename IN ({placeholders})
        )
      GROUP BY t.id
    '''

    vals = (
      user_discord_id,
      user_discord_id,
      *badge_filenames,
      *badge_filenames
    )

    await query.execute(sql, vals)
    trades = query.fetchall()
    return trades


# _________                __  .__                           .___
# \_   ___ \  ____   _____/  |_|__| ____  __ __ __ __  _____ |   | _____ _____     ____   ____   ______
# /    \  \/ /  _ \ /    \   __\  |/    \|  |  \  |  \/     \|   |/     \\__  \   / ___\_/ __ \ /  ___/
# \     \___(  <_> )   |  \  | |  |   |  \  |  /  |  /  Y Y  \   |  Y Y  \/ __ \_/ /_/  >  ___/ \___ \
#  \______  /\____/|___|  /__| |__|___|  /____/|____/|__|_|  /___|__|_|  (____  /\___  / \___  >____  >
#         \/            \/             \/                  \/          \/     \//_____/      \/     \/

# TO DO: Need to refactor these into the pipeline functions in `utils.image_utils`

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