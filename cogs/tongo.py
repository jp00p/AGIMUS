from common import *
from handlers.xp import increment_user_xp

from utils.badge_utils import *
from utils.badge_instances import *
from utils.check_channel_access import access_check
from utils.check_user_access import user_check

from queries.tongo import *
from queries.badge_info import *
from queries.badge_instances import *
from queries.wishlist import *

f = open("./data/rules_of_acquisition.txt", "r")
data = f.read()
rules_of_acquisition = data.split("\n")
f.close()


TONGO_AUTO_CONFRONT_TIMEOUT = timedelta(hours=8)
MINIMUM_LIQUIDATION_CONTINUUM = 5
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
        title="DOWNTIME DETECTED! Auto-confronting Tongo...",
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
      await self._perform_confront(active_tongo, chair, auto_confront=True)
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
                    f"This Tongo game has {humanize.naturaltime(time_left)} left before the game is automatically ended!",
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
    description="Begin a game of Tongo!"
  )
  @option(
    name="liability",
    description="Risk 3 badges from your unlocked inventory or your FULL inventory!).",
    choices=[
      discord.OptionChoice(name="Unlocked", value="unlocked"),
      discord.OptionChoice(name="All In", value="all_in")
    ],
    required=True
  )
  async def venture(self, ctx: discord.ApplicationContext, liability: str):
    await ctx.defer(ephemeral=True)
    user_id = ctx.author.id
    member = await self.bot.current_guild.fetch_member(user_id)

    existing_game = await db_get_open_game()
    if existing_game:
      if await db_is_user_in_game(existing_game['id'], user_id):
        description = "You've already joined this Tongo game!"
        if user_id == existing_game['chair_user_id']:
          description += f"\n\nPlus you're the one that started it! If you want to deal em out, use `/tongo confront`!"
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

    if liability == 'unlocked':
      badge_instances = await db_get_user_badge_instances(user_id, locked=False)
    else:
      badge_instances = await db_get_user_badge_instances(user_id)

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
        description = "You don't possess any badges!"
      elif liability == 'unlocked':
        description = "All of the Unlocked Badges you possess are already in the Continuum!"
      else:
        description = "All of the Badges in your collection are already in the Continuum!"

      footer_text = "Try unlocking some others!" if liability == 'unlocked' and len(all_ids) > 0 else ""
      embed = discord.Embed(
        title="No Badges Viable For Random Selection!",
        description=description,
        color=discord.Color.red()
      )
      if footer_text:
        embed.set_footer(text=footer_text)
      await ctx.followup.send(embed=embed, ephemeral=True)
      return

    eligible = [b for b in badge_instances if b['badge_info_id'] not in continuum_badge_ids and b['badge_info_id'] not in special_badge_ids]

    if len(eligible) < 3:
      footer_text = "Try unlocking some others!" if liability == 'unlocked' else ""
      embed = discord.Embed(
        title="Not Enough Viable Badges Available!",
        description=f"You only have {len(eligible)} available to randomly select — you need at least 3!",
        color=discord.Color.red()
      )
      if footer_text:
        embed.set_footer(text=footer_text)
      await ctx.followup.send(embed=embed, ephemeral=True)
      return

    selected = random.sample(eligible, 3)

    game_id = await db_create_tongo_game(user_id)
    await db_add_game_player(game_id, user_id, liability)

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
                  f"They threw in 3 badges {'from their unlocked inventory' if liability == 'unlocked' else 'from their entire collection'} into the Great Material Continuum.\n\n"
                  "Only *they* can confront using `/tongo confront`. If they don't act within 8 hours, the system will auto-confront!",
      color=discord.Color.dark_purple()
    )
    embed.add_field(
      name=f"Badges Ventured By {member.display_name}",
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
    name="liability",
    description="Risk 3 badges from your unlocked inventory or your FULL inventory.!).",
    choices=[
      discord.OptionChoice(name="Unlocked", value="unlocked"),
      discord.OptionChoice(name="All In", value="all_in")
    ],
    required=True
  )
  async def risk(self, ctx: discord.ApplicationContext, liability: str):
    await ctx.defer(ephemeral=True)
    user_id = ctx.author.id
    member = await self.bot.current_guild.fetch_member(user_id)

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
        description += f"\n\nPlus you're the one that started it! If you want to deal em out, use `/tongo confront`!"
      await ctx.followup.send(embed=discord.Embed(
        title="Already Participating",
        description=description,
        color=discord.Color.red()
      ), ephemeral=True)
      return

    if liability == 'unlocked':
      badge_instances = await db_get_user_badge_instances(user_id, locked=False)
    else:
      badge_instances = await db_get_user_badge_instances(user_id)

    if len(badge_instances) < 3:
      await ctx.followup.send(embed=discord.Embed(
        title="Not Enough Badges",
        description="You need at least 3 eligible badges to join Tongo!",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    continuum_badge_info_ids = await db_get_continuum_badge_info_ids()
    special_badge_ids = [b['id'] for b in await db_get_special_badge_info()]

    eligible = [b for b in badge_instances if b['badge_info_id'] not in continuum_badge_info_ids and b['badge_info_id'] not in special_badge_ids]

    if len(eligible) < 3:
      await ctx.followup.send(embed=discord.Embed(
        title="Not Enough Viable Badges",
        description=f"You only have {len(eligible)} badges eligible to throw in — you need at least 3!",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    selected = random.sample(eligible, 3)
    await db_add_game_player(game['id'], user_id, liability)

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
    description = f"### **{member.display_name}** has joined the table!\n\nA new challenger appears! Player {player_count} has entered the game with 3 badges {'from their unlocked inventory' if liability == 'unlocked' else 'from their entire collection'}!"
    if self.auto_confront.next_iteration:
      description += f"\n\nThis Tongo game will automatically confront {humanize.naturaltime(self.auto_confront.next_iteration)}."

    embed = discord.Embed(
      title="TONGO! Badges Risked!",
      description=description,
      color=discord.Color.dark_purple()
    )
    embed.add_field(
      name=f"Badges Risked By {member.display_name}",
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


  # TODO: Re-implement this once we get the badge_instance trading stuff complete
  # async def _cancel_tongo_related_trades(self, user_discord_id, selected_badges):
  #   # These are all the active or pending trades that involved the user as either the
  #   # requestee or requestor and include the badges that were added to the tongo pot
  #   # are thus no longer valid and need to be canceled
  #   trades_to_cancel = await db_get_related_tongo_badge_trades(user_discord_id, selected_badges)
  #   if not trades_to_cancel:
  #     return

  #   # Iterate through to cancel, and then
  #   for trade in trades_to_cancel:
  #     await db_cancel_trade(trade)
  #     requestee = await self.bot.current_guild.fetch_member(trade['requestee_id'])
  #     requestor = await self.bot.current_guild.fetch_member(trade['requestor_id'])

  #     offered_badge_names, requested_badge_names = await get_offered_and_requested_badge_names(trade)

  #     # Give notice to Requestee
  #     user = await get_user(requestee.id)
  #     if user["receive_notifications"] and trade['status'] == 'active':
  #       try:
  #         requestee_embed = discord.Embed(
  #           title="Trade Canceled",
  #           description=f"Just a heads up! Your USS Hood Badge Trade initiated by **{requestor.display_name}** was canceled because one or more of the badges involved were added to the Tongo pot!",
  #           color=discord.Color.purple()
  #         )
  #         requestee_embed.add_field(
  #           name=f"Offered by {requestor.display_name}",
  #           value=offered_badge_names
  #         )
  #         requestee_embed.add_field(
  #           name=f"Requested from {requestee.display_name}",
  #           value=requested_badge_names
  #         )
  #         requestee_embed.set_footer(
  #           text="Note: You can use /settings to enable or disable these messages."
  #         )
  #         await requestee.send(embed=requestee_embed)
  #       except discord.Forbidden as e:
  #         logger.info(f"Unable to send trade cancelation message to {requestee.display_name}, they have their DMs closed.")
  #         pass

  #     # Give notice to Requestor
  #     user = await get_user(requestor.id)
  #     if user["receive_notifications"]:
  #       try:
  #         requestor_embed = discord.Embed(
  #           title="Trade Canceled",
  #           description=f"Just a heads up! Your USS Hood Badge Trade requested from **{requestee.display_name}** was canceled because one or more of the badges involved were added to the Tongo pot!",
  #           color=discord.Color.purple()
  #         )
  #         requestor_embed.add_field(
  #           name=f"Offered by {requestor.display_name}",
  #           value=offered_badge_names
  #         )
  #         requestor_embed.add_field(
  #           name=f"Requested from {requestee.display_name}",
  #           value=requested_badge_names
  #         )
  #         requestor_embed.set_footer(
  #           text="Note: You can use /settings to enable or disable these messages."
  #         )
  #         await requestor.send(embed=requestor_embed)
  #       except discord.Forbidden as e:
  #         logger.info(f"Unable to send trade cancelation message to {requestor.display_name}, they have their DMs closed.")
  #         pass

  #    ____        __
  #   /  _/__  ___/ /____ __
  #  _/ // _ \/ _  / -_) \ /
  # /___/_//_/\_,_/\__/_\_\
  @tongo.command(
    name="index",
    description="Check the current status of the active game of Tongo!"
  )
  @commands.check(access_check)
  @commands.check(user_check)
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
      description += f"\n\nThis Tongo game will automatically confront {humanize.naturaltime(self.auto_confront.next_iteration)}."

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

  #   _____          ___              __
  #  / ___/__  ___  / _/______  ___  / /_
  # / /__/ _ \/ _ \/ _/ __/ _ \/ _ \/ __/
  # \___/\___/_//_/_//_/  \___/_//_/\__/
  @tongo.command(
  name="confront",
  description="If you're The Chair, end the current game of Tongo!"
  )
  @commands.check(access_check)
  @commands.check(user_check)
  async def confront(self, ctx:discord.ApplicationContext):
    await ctx.defer(ephemeral=True)
    user_id = ctx.author.id

    active_game = await db_get_open_game()
    if not active_game:
      await ctx.followup.send(embed=discord.Embed(
        title="No Tongo Game In Progress",
        description="No one is playing Tongo yet!\n\nUse `/tongo venture` to begin a game!",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    if int(active_game['chair_user_id']) != user_id:
      chair = await self.bot.current_guild.fetch_member(active_game['chair_user_id'])
      await ctx.followup.send(embed=discord.Embed(
        title="You're Not The Chair!",
        description=f"Only The Chair is allowed to end the Tongo!\n\nThe current Chair is: **{chair.display_name}**",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    players = await db_get_players_for_game(active_game['id'])
    if len(players) < 2:
      embed = discord.Embed(
        title="You're The Only Player!",
        description="Can't do a Confront when you're the only player in the game! Invite some people!",
        color=discord.Color.red()
      )
      embed.set_footer(text="It takes Two to Tongo...")
      await ctx.followup.send(embed=embed, ephemeral=True)
      return

    await ctx.followup.send(embed=discord.Embed(
      title="Confront Acknowledged!",
      description="Ending the game and preparing distribution...",
      color=discord.Color.dark_purple()
    ), ephemeral=True)

    chair = await self.bot.current_guild.fetch_member(user_id)
    await self._perform_confront(active_game, chair, auto_confront=False)
    await db_update_game_status(active_game['id'], 'resolved')

    # Stop auto-confront loop if it exists
    try:
      self.auto_confront.cancel()
    except Exception:
      pass


  #    ___       __           _____          ___              __
  #   / _ |__ __/ /____  ____/ ___/__  ___  / _/______  ___  / /_
  #  / __ / // / __/ _ \/___/ /__/ _ \/ _ \/ _/ __/ _ \/ _ \/ __/
  # /_/ |_\_,_/\__/\___/    \___/\___/_//_/_//_/  \___/_//_/\__/
  @tasks.loop(hours=8)
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


  async def _perform_confront(self, active_tongo, active_chair, auto_confront=False):
    player_distribution = await self._execute_confront_distribution(active_tongo['id'])
    player_ids = list(player_distribution.keys())

    remaining_badges = await db_get_full_continuum_badges()

    # Handle potential liquidation
    liquidation_result = None
    if auto_confront:
      liquidation_result = await self._handle_liquidation(active_tongo['id'], remaining_badges, player_ids)

    # Build and send results embed
    results_embed = await build_confront_results_embed(active_chair, auto_confront, remaining_badges)
    zeks_table = await self.bot.fetch_channel(get_channel_id("zeks-table"))
    channel_message = await zeks_table.send(embed=results_embed)

    # Show per-player rewards
    for user_id, badge_instance_ids in player_distribution.items():
      member = await self.bot.current_guild.fetch_member(user_id)
      wishlist = await db_get_user_wishlist_badges(user_id)

      if badge_instance_ids:
        badges_received = [
          await db_get_badge_info_by_instance_id(instance_id)
          for instance_id in badge_instance_ids
        ]
        filenames = [b['badge_filename'] for b in badges_received]

        image_id = f"{active_tongo['id']}-won-{user_id}"
        showcase_image = await generate_badge_trade_showcase(
          filenames,
          image_id,
          f"Badges Won By {member.display_name}",
          f"{len(badges_received)} Badges"
        )

        wishlist_received = [b for b in wishlist if b['badge_filename'] in filenames]
        wishlist_filenames_received = [b['badge_filename'] for b in wishlist_received]

        xp_awarded = 0
        if len(badge_instance_ids) < 3:
          xp_awarded = 110 * (3 - len(badge_instance_ids))
          if datetime.today().weekday() >= 4:
            xp_awarded *= 2
          await increment_user_xp(member, xp_awarded, 'tongo_loss', zeks_table, "Consolation Prize for Tongo Loss")

        player_embed = await build_confront_player_embed(member, badges_received, wishlist_filenames_received, xp_awarded)
        player_embed.set_image(url=f"attachment://{image_id}.png")
        await zeks_table.send(embed=player_embed, file=showcase_image)

        dm_embed = build_confront_dm_embed(member, badges_received, wishlist_filenames_received, channel_message.jump_url, auto_confront, xp_awarded)
        try:
          await member.send(embed=dm_embed)
        except discord.Forbidden:
          logger.info(f"Unable to DM {member.display_name} — DMs closed.")
      else:
        xp_awarded = 110 * 3
        if datetime.today().weekday() >= 4:
          xp_awarded *= 2
        await increment_user_xp(member, xp_awarded, 'tongo_loss', zeks_table, "Consolation Prize for Tongo Loss")

        channel_embed = build_confront_no_rewards_embed(member, xp_awarded)
        await zeks_table.send(embed=channel_embed)

        dm_embed = build_confront_dm_embed(member, [], [], channel_message.jump_url, auto_confront, xp_awarded)
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
      image_id = f"{active_tongo['id']}-liquidation-{member.id}"
      image_file = await generate_badge_trade_showcase([reward['badge_filename']], image_id, f"Zek's Endowment For {member.display_name}", "Greed is Eternal!")
      await zeks_table.send(embed=build_liquidation_endowment_embed(member, image_id), file=image_file)

      # Liquidated image
      removal_id = f"{active_tongo['id']}-liquidation_badges"
      removal_file = await generate_badge_trade_showcase([b['badge_filename'] for b in removed], removal_id, "Badges Liquidated", f"{len(removed)} Badges Liquidated")
      await zeks_table.send(embed=build_liquidation_removal_embed(removed, removal_id), file=removal_file)

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

    # Build wishlist and owned badge_info_id sets
    for player_id in player_ids:
      inventory = await db_get_owned_badge_filenames_by_user_id(player_id)  # badge_filenames
      inventory_info_ids = set()
      for item in inventory:
        info = await db_get_badge_info_by_filename(item['badge_filename'])
        if info:
          inventory_info_ids.add(info['id'])

      wishlist = await db_get_user_wishlist_badges(player_id)
      wishlist_info_ids = set(b['id'] for b in wishlist)

      player_inventories[player_id] = inventory_info_ids
      player_wishlists[player_id] = wishlist_info_ids

    # Shuffle for fairness
    random.shuffle(player_ids)
    random.shuffle(continuum_records)

    turn_index = 0
    players_with_max_badges = set()
    players_with_no_assignable_badges = set()

    while continuum_records and (len(players_with_max_badges) + len(players_with_no_assignable_badges)) < len(player_ids):
      current_player = player_ids[turn_index % len(player_ids)]

      if current_player in players_with_max_badges or current_player in players_with_no_assignable_badges:
        turn_index += 1
        continue

      selected_badge = None
      for badge in continuum_records:
        info_id = badge['badge_info_id']

        if info_id in player_wishlists[current_player] and info_id not in player_inventories[current_player]:
          selected_badge = badge
          break
        elif info_id not in player_inventories[current_player]:
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

    # Associate the badge_instances with the winners
    for player_user_id, reward_badge_instances in player_distribution.items():
      for instance_id in reward_badge_instances:
        await transfer_badge_instance(instance_id, player_user_id, event_type='tongo_reward')
        await db_add_game_reward(game_id, player_user_id, instance_id)

    # Remove the badges from the Continuum
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
    await db_autolock_badges_by_filenames_if_in_wishlist(beneficiary_id, [reward_instance['badge_filename']])
    await db_purge_users_wishlist(beneficiary_id)

    liquidation_result['reward_instance_id'] = reward_instance['badge_instance_id']
    return liquidation_result


  async def _determine_liquidation(self, continuum: list[dict], tongo_players: list[int]) -> Optional[dict]:
    logger.info("hmmmm...")
    players = tongo_players.copy()
    random.shuffle(players)

    for player_id in players:
      wishlist_badges = await db_get_user_wishlist_badges(player_id)
      if not wishlist_badges:
        continue

      inventory_filenames = set(b['badge_filename'] for b in await db_get_owned_badge_filenames_by_user_id(player_id))
      wishlist_to_grant = [b for b in wishlist_badges if b['badge_filename'] not in inventory_filenames]

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
      logger.info(pprint(liquidation_result))

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
async def build_confront_results_embed(active_chair: discord.Member, auto_confront: bool, remaining_badges: list[dict]) -> discord.Embed:
  if auto_confront:
    title = "TONGO! Game Automatically Ending!"
    description= f"The game started by **{active_chair.display_name}** has run out of time!\n\nEnding the game!"
  else:
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


def build_confront_dm_embed(member: discord.Member, badge_infos: list[dict], wishlist_badge_filenames: list[str], jump_url: str, auto_confront: bool, xp_awarded: int = 0) -> discord.Embed:
  if auto_confront:
    title = "TONGO! Game Automatically Ending!"
    description= f"Heya {member.display_name}! Time ran out for your Tongo game and it has automatically ended!"
  else:
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


def build_liquidation_endowment_embed(member: discord.Member, image_id: str) -> discord.Embed:
  embed = discord.Embed(
    title="Liquidation Endowment",
    description=(
      f"As the ✨ *Lucky Liquidation Beneficiary* ✨ **{member.display_name}** has been granted a freshly-minted, randomized badge from their wishlist!"
    ),
    color=discord.Color.gold()
  )
  embed.set_image(url=f"attachment://{image_id}.png")
  return embed


def build_liquidation_removal_embed(badges: list[dict], image_id: str) -> discord.Embed:
  embed = discord.Embed(
    title="Badges Liquidated",
    description="The following badges have been removed from The Great Material Continuum...",
    color=discord.Color.gold()
  )
  embed.set_image(url=f"attachment://{image_id}.png")
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

      FROM instance_trades AS t
      LEFT JOIN trade_offered_instances AS to_i ON t.id = to_i.trade_id
      LEFT JOIN trade_requested_instances AS tr_i ON t.id = tr_i.trade_id

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