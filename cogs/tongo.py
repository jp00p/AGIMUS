from collections import defaultdict

from common import *

from cogs.trade import get_offered_and_requested_badge_names

from queries.badge_info import *
from queries.badge_instances import *
from queries.crystal_instances import *
from queries.tongo import *
from queries.trade import db_cancel_trade, db_get_global_in_progress_trade_instance_ids
from queries.wishlists import *

from utils.badge_instances import *
from utils.badge_trades import *
from utils.badge_utils import *
from utils.crystal_instances import *
from utils.check_channel_access import access_check
from utils.check_user_access import user_check
from utils.database import AgimusTransactionDB
from utils.exception_logger import log_manual_exception
from utils.image_utils import *
from utils.prestige import *
from utils.string_utils import escape_discord_formatting as edf

f = open("./data/rules_of_acquisition.txt", "r")
data = f.read()
rules_of_acquisition = data.split("\n")
f.close()


TONGO_AUTO_CONFRONT_TIMEOUT = timedelta(hours=6)
MINIMUM_LIQUIDATION_CONTINUUM = 25
MINIMUM_LIQUIDATION_PLAYERS = 5
MINIMUM_AVARICE_QUOTIENT = 21
DIVIDEND_REWARDS = {
  "buffer": {"cost": 3, "label": "Crystal Pattern Buffer"},
  "wishlist": {"cost": 7, "label": "Guaranteed Wishlist Badge"},
  "replication": {"cost": 11, "label": "Ferengi Crystal Replicator Override"},
}

class TongoDividendsView(discord.ui.View):
  def __init__(self, cog, balance: int):
    super().__init__(timeout=120)
    self.cog = cog
    self.redeem_buffer.disabled = balance < DIVIDEND_REWARDS['buffer']['cost']
    self.redeem_wishlist.disabled = balance < DIVIDEND_REWARDS['wishlist']['cost']
    self.redeem_replication.disabled = balance < DIVIDEND_REWARDS['replication']['cost']

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    self.interaction_user = interaction.user
    return True

  @discord.ui.button(label=f"{DIVIDEND_REWARDS['buffer']['label']}", custom_id="redeem_buffer", style=discord.ButtonStyle.blurple)
  async def redeem_buffer(self, button, interaction: discord.Interaction):
    await self.handle_redeem(interaction, reward_id="buffer")

  @discord.ui.button(label=f"{DIVIDEND_REWARDS['wishlist']['label']}", custom_id="redeem_wishlist", style=discord.ButtonStyle.blurple)
  async def redeem_wishlist(self, button, interaction: discord.Interaction):
    await self.handle_redeem(interaction, reward_id="wishlist")

  @discord.ui.button(label=f"{DIVIDEND_REWARDS['replication']['label']}", custom_id="redeem_replication", style=discord.ButtonStyle.blurple)
  async def redeem_replication(self, button, interaction: discord.Interaction):
    await self.handle_redeem(interaction, reward_id="replication")

  async def handle_redeem(self, interaction: discord.Interaction, reward_id: str):
    await interaction.response.defer()

    user_id = interaction.user.id
    reward = DIVIDEND_REWARDS.get(reward_id)
    if not reward:
      await interaction.followup.edit_message(
        message_id=interaction.message.id,
        embed=discord.Embed(
          title="Invalid Reward!",
          color=discord.Color.red()
        ), ephemeral=True
      )
      return

    record = await db_get_tongo_dividends(user_id)
    balance = record['current_balance'] if record else 0
    if balance < reward['cost']:
      await interaction.followup.edit_message(
        message_id=interaction.message.id,
        embed=discord.Embed(
          title="Insufficient Dividend Balance!",
          description="You don't have enough Dividends to redeem that Reward!\n\n"
                     f"You currently possess **{balance}** Dividends and this reward requires **{reward['cost']}**!",
          color=discord.Color.red()
        ),
        view=None,
        ephemeral=True
      )
      return

    await interaction.followup.edit_message(
      message_id=interaction.message.id,
      embed=discord.Embed(
        title="Dividends Deducting...",
        description="I love the sound of Latinum clinking.",
        color=discord.Color.gold()
      ),
      view=None
    )

    # Reward fulfillment logic
    result_successful = False
    if reward_id == "buffer":
      result_successful = await self._reward_crystal_buffer(interaction, user_id)
    elif reward_id == "wishlist":
      result_successful = await self._reward_wishlist(interaction, user_id)
    elif reward_id == "replication":
      result_successful = await self._reward_replication(interaction, user_id)

    if not result_successful:
      return

    await db_decrement_user_tongo_dividends(user_id, reward['cost'])

    confirmation_embed = discord.Embed(
      title="Transaction Complete",
      description=f"A **{reward['label']}** has been granted and your Dividends balance has been deducted by **{reward['cost']}**.",
      color=discord.Color.gold()
    )
    confirmation_embed.set_footer(
      text=f"Greed is Eternal!",
      icon_url="https://i.imgur.com/scVHPNm.png"
    )
    confirmation_embed.set_image(url=random.choice(["https://i.imgur.com/s10kcx3.gif", "https://i.imgur.com/FTPiLy0.gif"]))
    # Edit the original message to show confirmation and remove this buttons view entirely
    await interaction.followup.edit_message(
      message_id=interaction.message.id,
      embed=confirmation_embed,
      view=None
    )


  async def _reward_crystal_buffer(self, interaction, user_id):
    member = await self.cog.bot.current_guild.fetch_member(user_id)

    await db_increment_user_crystal_buffer(user_id)

    embed = discord.Embed(
      title="Dividends Redeemed!",
      description=(
        f"An advantageous transaction has been arranged with Grand Nagus Zek!\n\n"
        f"**{edf(member.display_name)}** has redeemed **{DIVIDEND_REWARDS['buffer']['cost']}** Dividends and received a **{DIVIDEND_REWARDS['buffer']['label']}!**\n\n"
        "They can now use  `/crystals replicate` to materialize a freshly minted Crystal!"
      ),
      color=discord.Color.gold()
    )
    embed.set_image(url="https://i.imgur.com/V5jk2LJ.gif")
    embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
      icon_url="https://i.imgur.com/scVHPNm.png"
    )

    zeks_table = await self.cog.bot.fetch_channel(get_channel_id("zeks-table"))
    await zeks_table.send(embed=embed)
    return True

  async def _reward_wishlist(self, interaction, user_id):
    echelon_progress = await db_get_echelon_progress(user_id)
    prestige = echelon_progress['current_prestige_tier'] if echelon_progress else 0
    active_wants = await db_get_active_wants(user_id, prestige)

    inventory_filenames = set(b['badge_filename'] for b in await db_get_owned_badge_filenames(user_id, prestige=prestige))
    wishlist_to_grant = [b for b in active_wants if b['badge_filename'] not in inventory_filenames]

    if not wishlist_to_grant:
      await interaction.followup.edit_message(
        message_id=interaction.message.id,
        embed=discord.Embed(
          title="No Wishlist (or Wishlist Already Fulfilled)!",
          description="You need to set up your wishlist with `/wishlist add` before you can redeem this Dividend Reward!",
          color=discord.Color.red()
        ).set_footer(text="(No Dividends have been deducted)"),
        view=None
      )
      return False

    if len(wishlist_to_grant) < MINIMUM_AVARICE_QUOTIENT:
      await interaction.followup.edit_message(
        message_id=interaction.message.id,
        embed=discord.Embed(
          title="You're not greedy ENOUGH!",
          description=f"Zek requires a Minimum Avarice Quotient to grant a wishlist badge!\n\nYou'll need to expand your wishlist in order to redeem this Dividend Reward!",
          color=discord.Color.red()
        ).set_footer(text="(No Dividends have been deducted)"),
        view=None
      )
      return False

    random.shuffle(wishlist_to_grant)
    badge_to_grant = wishlist_to_grant[0]
    badge_info_id = badge_to_grant['badge_info_id']
    reward_instance = await create_new_badge_instance(user_id, badge_info_id, prestige_level=prestige, event_type='dividend_reward')

    discord_file, attachment_url = await generate_badge_preview(user_id, reward_instance)

    member = await self.cog.bot.current_guild.fetch_member(user_id)
    embed = discord.Embed(
      title="Dividends Redeemed!",
      description=(
        f"A profitable transaction has been arranged with Grand Nagus Zek!\n\n"
        f"**{edf(member.display_name)}** has redeemed **{DIVIDEND_REWARDS['wishlist']['cost']}** Dividends and received a **{DIVIDEND_REWARDS['wishlist']['label']}!**"
      ),
      color=discord.Color.gold()
    )
    embed.set_image(url=attachment_url)
    embed.add_field(
      name=f"Zek's Favor Grants...",
      value=f"* ✨ {reward_instance['badge_name']} [{PRESTIGE_TIERS[prestige]}] ✨",
      inline=False
    )
    embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
      icon_url="https://i.imgur.com/scVHPNm.png"
    )

    zeks_table = await self.cog.bot.fetch_channel(get_channel_id("zeks-table"))
    await zeks_table.send(
      embed=embed,
      file=discord_file
    )
    return True

  async def _reward_replication(self, interaction, user_id):
    member = await self.cog.bot.current_guild.fetch_member(user_id)

    # Override regular rank choices for Rare+ Chances
    rolled_rank = weighted_random_choice({
      3: 60,  # Rare
      4: 25,  # Legendary
      5: 12,  # Mythic
      6: 3    # Unobtanium
    })
    crystal_type = await db_select_random_crystal_type_by_rarity_rank(rolled_rank)
    crystal = await create_new_crystal_instance(user_id, crystal_type['id'])

    discord_file, replicator_confirmation_filename = await generate_crystal_replicator_confirmation_frames(crystal, replicator_type='ferengi')

    FERENGI_RARITY_SUCCESS_MESSAGES = {
      'rare': [
        "The Great Material Continuum smiles upon you, {user}!",
        "A *profitable* acquisition, {user}!",
        "According to Rule of Acquisition No. 9: Opportunity plus instinct equals profit - and you, {user}, just proved it!"
      ],
      'legendary': [
        "Now *that's* a high-value return {user}!",
        "Market volatility in your favor! A ***Legendary*** score, {user}!",
        "Rule No. 45: 'Expand or die.' You've just expanded your holdings *dramatically*, {user}!"
      ],
      'mythic': [
        "*My lobes are tingling!* A ***MYTHIC*** crystal for {user}!? Unthinkable... " + f"{get_emoji('quark_ooh_excited')}",
        "**MYTHIC!?!** Even Brunt, FCA, is impressed by (and suspicious of...) {user}'s new acquisition! " + f"{get_emoji('quark_cool')}",
        "Mythic? **MYTHIC!?** By the ears of Zek, {user}, you've just tipped the economic axis of the quadrant! " + f"{get_emoji('quark_profit_zoom')}"
      ],
      'unobtainium': [
        "{user} who did you *bribe* or *blackmail* to grant access to *THIS* one?",
        "::FIRMWARE CORRUPTION:: Overrides look overclocked, {user} must have installed an illegal rootkit...",
        "The FCA will be conducting a *thorough* audit after this result, better take the money and run {user}!"
      ]
    }

    success_message = random.choice(FERENGI_RARITY_SUCCESS_MESSAGES[crystal['rarity_name'].lower()]).format(user=member.mention)
    channel_embed = discord.Embed(
      title='Dividends Redeemed!',
      description=f"**{edf(member.display_name)}** has redeemed **{DIVIDEND_REWARDS['replication']['cost']}** Dividends and the use of a **{DIVIDEND_REWARDS['replication']['label']}!**\n\n"
                  f"Grand Nagus Zek pulls a Honeystick out from within his robes, wanders over to the Replicator behind the bar, the familiar hum fills the air, and the result is...\n\n> **{crystal['crystal_name']}**!"
                  f"\n\n{success_message}",
      color=discord.Color.gold()
    )
    channel_embed.add_field(name=f"Rank", value=f"> {crystal['emoji']}  {crystal['rarity_name']}", inline=False)
    channel_embed.add_field(name=f"Description", value=f"> {crystal['description']}", inline=False)
    channel_embed.set_image(url=f"attachment://{replicator_confirmation_filename}")
    channel_embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
      icon_url="https://i.imgur.com/scVHPNm.png"
    )

    zeks_table = await self.cog.bot.fetch_channel(get_channel_id("zeks-table"))
    await zeks_table.send(
      embed=channel_embed,
      files=[discord_file]
    )

    return True

class TongoPaginator(pages.Paginator):
  async def on_timeout(self):
    # Reset to first page
    await self.goto_page(page_number=0)
    # Then disable view
    await super().on_timeout()

# ___________                          _________
# \__    ___/___   ____    ____   ____ \_   ___ \  ____   ____
#   |    | /  _ \ /    \  / ___\ /  _ \/    \  \/ /  _ \ / ___\
#   |    |(  <_> )   |  \/ /_/  >  <_> )     \___(  <_> ) /_/  >
#   |____| \____/|___|  /\___  / \____/ \______  /\____/\___  /
#                     \//_____/                \/      /_____/
class Tongo(commands.Cog):
  def __init__(self, bot):
    self.bot: commands.Bot = bot
    self.tongo_buttons = [
      pages.PaginatorButton("prev", label="⬅", style=discord.ButtonStyle.primary, row=1),
      pages.PaginatorButton(
        "page_indicator", style=discord.ButtonStyle.gray, disabled=True, row=1
      ),
      pages.PaginatorButton("next", label="➡", style=discord.ButtonStyle.primary, row=1),
    ]
    self.first_auto_confront = True
    self.block_new_games = False

  tongo = discord.SlashCommandGroup("tongo", "Commands for Tongo Badge Game")

  #   _    _    _
  #  | |  (_)__| |_ ___ _ _  ___ _ _ ___
  #  | |__| (_-<  _/ -_) ' \/ -_) '_(_-<
  #  |____|_/__/\__\___|_||_\___|_| /__/
  @commands.Cog.listener()
  async def on_ready(self):
    settings = await db_get_tongo_settings()
    self.block_new_games = settings['block_new_games']
    if not self.block_new_games:
      confront_needed = await self._ensure_auto_confront_active_or_confront_needed("reboot")
      if confront_needed:
        await self._trigger_necessary_autoconfront("reboot")

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
  @commands.check(access_check)
  async def venture(self, ctx: discord.ApplicationContext, prestige: str):
    await ctx.defer(ephemeral=True)

    if self.block_new_games:
      zeks_table = await self.bot.fetch_channel(get_channel_id("zeks-table"))
      megalomaniacal = await bot.current_guild.fetch_channel(get_channel_id("megalomaniacal-computer-storage"))
      await ctx.followup.send(
        embed=discord.Embed(
          title="Tongo Temporarily Disabled",
          description=f"Tongo games are currently on hiatus for a minute.\n\nStay tuned to messages here is {zeks_table.mention} and/or {megalomaniacal.mention} for updates.",
          color=discord.Color.orange()
        ),
        ephemeral=True
      )
      return

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
    special_badge_ids = [b['id'] for b in await db_get_special_badge_info()]
    in_progress_trade_instance_ids = await db_get_global_in_progress_trade_instance_ids()
    existing_pairs = await db_get_continuum_badge_info_prestige_pairs()
    potential = [
      b for b in badge_instances
      if (b['badge_info_id'], b['prestige_level']) not in existing_pairs and
        b['badge_info_id'] not in special_badge_ids
    ]
    eligible = [
      b for b in potential
      if b['badge_instance_id'] not in in_progress_trade_instance_ids
    ]

    if len(eligible) < 3:
      description = f"You only have {len(eligible)} {prestige_tier} badges eligible to throw in — you need at least 3!"
      num_removed_due_to_trade = len(potential) - len(eligible)
      if num_removed_due_to_trade >= 1:
        description += (
          f"\n\n-# Note that {num_removed_due_to_trade} badges were deemed ineligible because they are involved in pending trades. "
          "You may want to review your outgoing or incoming trades with `/trade send` and `/trade incoming` before attempting again!"
        )
      await ctx.followup.send(
        embed=discord.Embed(
          title=f"Not Enough Viable {prestige_tier} Badges to Venture!",
          description=description,
          color=discord.Color.red()
        ).set_footer(text="Try unlocking some others!"),
        ephemeral=True
      )
      return

    selected = random.sample(eligible, 3)

    game_id = await db_create_tongo_game(user_id)
    await db_add_game_player(game_id, user_id)

    ventured_badges = [await db_get_badge_instance_by_badge_info_id(user_id, b['badge_info_id'], prestige=prestige) for b in selected]

    # Toss the badges in!
    for instance in selected:
      await throw_badge_into_continuum(instance, user_id, current_game_id=game_id)
    # Grant the user a dividend for playing
    await self._cancel_tongo_related_trades(user_id, selected)
    await db_increment_tongo_dividends(user_id)

    await ctx.followup.send(
      embed=discord.Embed(
        title="Venture Acknowledged!",
        description="You've started a new game of Tongo.",
        color=discord.Color.dark_purple()
      ),
      ephemeral=True
    )

    continuum_badges = await db_get_full_continuum_badges()

    # Create initial Venture embed and toss it into the pagination pages
    embed = discord.Embed(
      title="TONGO! Badges Ventured!",
      description=f"**{edf(member.display_name)}** has begun a new game of Tongo!\n\n"
                  f"They threw in **3 {prestige_tier} Badges** from their unlocked/uncrystallized inventory into the Great Material Continuum, and they have been granted **1** Tongo Dividend.\n\n"
                  "The wheel is spinning, the game will end in 6 hours, and then the badges will be distributed!",
      color=discord.Color.dark_purple()
    )
    embed.add_field(
      name=f"{prestige_tier} Badges Ventured By {edf(member.display_name)}",
      value="\n".join([f"* {b['badge_name']} [{PRESTIGE_TIERS[b['prestige_level']]}]" for b in ventured_badges]),
      inline=False
    )
    embed.add_field(
      name="The Great Material Continuum",
      value=f"{len(continuum_badges)} Total Badges\n-# See following pages for details!",
      inline=False
    )
    embed.set_image(url="https://i.imgur.com/tRi1vYq.gif")
    embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
      icon_url="https://i.imgur.com/GTN4gQG.jpg"
    )
    tongo_pages = [pages.Page(embeds=[embed])]

    # Chunk the continuum into 20-badge chunks
    continuum_chunks = [continuum_badges[i:i + 20] for i in range(0, len(continuum_badges), 20)]
    for page_idx, t_chunk in enumerate(continuum_chunks):
      embed = discord.Embed(
        title=f"The Great Material Continuum (Page {page_idx + 1} of {len(continuum_chunks)})",
        color=discord.Color.dark_purple()
      )
      embed.add_field(
        name="Total Badges in the Continuum!",
        value="\n".join([f"* {b['badge_name']} [{PRESTIGE_TIERS[b['prestige_level']]}]" for b in t_chunk]),
        inline=False
      )
      embed.set_footer(
        text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
        icon_url="https://i.imgur.com/GTN4gQG.jpg"
      )
      tongo_pages.append(pages.Page(embeds=[embed]))

    # Include Continuum Images within Embed Pages
    continuum_images = await generate_paginated_continuum_images(continuum_badges)
    file_chunks = [continuum_images[i:i + 10] for i in range(0, len(continuum_images), 10)]
    for chunk in file_chunks:
      for file in chunk:
        continuum_page = pages.Page(
          embeds=[
            discord.Embed(
              color=discord.Color.dark_gold()
            ).set_image(url=f"attachment://{file.filename}")
          ],
          files=[file]
        )
        tongo_pages.append(continuum_page)

    # Send Risk Details as Paginator
    continuum_paginator = TongoPaginator(
      pages=tongo_pages,
      show_indicator=True,
      custom_buttons=self.tongo_buttons,
      use_default_buttons=False,
      timeout=300
    )
    await continuum_paginator.respond(ctx.interaction, ephemeral=False)

    # Autoconfront
    self.auto_confront.cancel()
    self.first_auto_confront = True
    self.auto_confront.change_interval(seconds=TONGO_AUTO_CONFRONT_TIMEOUT.total_seconds())
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
  @commands.check(access_check)
  async def risk(self, ctx: discord.ApplicationContext, prestige: str):
    await ctx.defer(ephemeral=True)

    zeks_table = await self.bot.fetch_channel(get_channel_id("zeks-table"))
    if self.block_new_games:
      megalomaniacal = await bot.current_guild.fetch_channel(get_channel_id("megalomaniacal-computer-storage"))
      await ctx.followup.send(
        embed=discord.Embed(
          title="Tongo Temporarily Disabled",
          description=f"Tongo games are currently on hiatus for a minute.\n\nStay tuned to messages here is {zeks_table.mention} and/or {megalomaniacal.mention} for updates.",
          color=discord.Color.orange()
        ),
        ephemeral=True
      )
      return

    # Ensure that the FUCKING TIMER is working
    confront_needed = await self._ensure_auto_confront_active_or_confront_needed("risk")

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
    special_badge_ids = [b['id'] for b in await db_get_special_badge_info()]
    in_progress_trade_instance_ids = await db_get_global_in_progress_trade_instance_ids()
    existing_pairs = await db_get_continuum_badge_info_prestige_pairs()
    potential = [
      b for b in badge_instances
      if (b['badge_info_id'], b['prestige_level']) not in existing_pairs and
        b['badge_info_id'] not in special_badge_ids
    ]
    eligible = [
      b for b in potential
      if b['badge_instance_id'] not in in_progress_trade_instance_ids
    ]

    if len(eligible) < 3:
      description = f"You only have {len(eligible)} {prestige_tier} badges eligible to throw in — you need at least 3!"
      num_removed_due_to_trade = len(potential) - len(eligible)
      if num_removed_due_to_trade >= 1:
        description += (
          f"\n\n-# Note that {num_removed_due_to_trade} badges were deemed ineligible because they are involved in pending trades. "
          "You may want to review your outgoing or incoming trades with `/trade send` and `/trade incoming` before attempting again!"
        )
      await ctx.followup.send(
        embed=discord.Embed(
          title=f"Not Enough Viable {prestige_tier} Badges to Venture!",
          description=description,
          color=discord.Color.red()
        ).set_footer(text="Try unlocking some others!"),
        ephemeral=True
      )
      return

    selected = random.sample(eligible, 3)
    await db_add_game_player(game['id'], user_id)

    risked_badges = [await db_get_badge_instance_by_badge_info_id(user_id, b['badge_info_id'], prestige=prestige) for b in selected]

    # Toss the badges in!
    for instance in selected:
      await throw_badge_into_continuum(instance, user_id, current_game_id=game['id'])
    await self._cancel_tongo_related_trades(user_id, selected)
    # Grant the user a dividend for playing
    await db_increment_tongo_dividends(user_id)

    await ctx.followup.send(embed=discord.Embed(
      title="Risk Acknowledged!",
      color=discord.Color.dark_purple()
    ), ephemeral=True)

    # Get player and continuum state for embeds
    players = await db_get_players_for_game(game['id'])
    player_ids = [p['user_discord_id'] for p in players]
    player_members = [await self.bot.current_guild.fetch_member(pid) for pid in player_ids]

    # Chunk the continuum into 20-badge chunks
    continuum_badges = await db_get_full_continuum_badges()
    continuum_chunks = [continuum_badges[i:i + 20] for i in range(0, len(continuum_badges), 20)]
    player_count = len(player_members)

    # Embed flavor
    description = f"### **{edf(member.display_name)}** has joined the table!\n\nA new challenger appears! Player {player_count} has entered the game with **3 {prestige_tier} Badges** from their unlocked/uncrystallized inventory, and they have been granted **1** Tongo Dividend!"
    if self.auto_confront.next_iteration:
      description += f"\n\nThis Tongo game will confront {humanize.naturaltime(self.auto_confront.next_iteration)}."

    embed = discord.Embed(
      title=f"TONGO! {prestige_tier} Badges Risked!",
      description=description,
      color=discord.Color.dark_purple()
    )
    embed.add_field(
      name=f"{prestige_tier} Badges Risked By {edf(member.display_name)}",
      value="\n".join([f"* {b['badge_name']} [{PRESTIGE_TIERS[b['prestige_level']]}]" for b in risked_badges]),
      inline=False
    )
    embed.add_field(
      name=f"Current Players ({player_count})",
      value="\n".join([f"* {m.display_name}" for m in player_members]),
      inline=False
    )
    embed.add_field(
      name="The Great Material Continuum",
      value=f"{len(continuum_badges)} Badges\n-# See following pages for details!",
      inline=False
    )
    embed.set_image(url=random.choice(["https://i.imgur.com/zEvF7uO.gif", "https://i.imgur.com/iX9ZCpH.gif"]))
    embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
      icon_url="https://i.imgur.com/GTN4gQG.jpg"
    )

    tongo_pages = [pages.Page(embeds=[embed])]
    for page_idx, t_chunk in enumerate(continuum_chunks):
      embed = discord.Embed(
        title=f"The Great Material Continuum (Page {page_idx + 1} of {len(continuum_chunks)})",
        color=discord.Color.dark_purple()
      )
      embed.add_field(
        name="Total Badges in the Continuum!",
        value="\n".join([f"* {b['badge_name']} [{PRESTIGE_TIERS[b['prestige_level']]}]" for b in t_chunk]),
        inline=False
      )
      embed.set_footer(
        text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
        icon_url="https://i.imgur.com/GTN4gQG.jpg"
      )
      tongo_pages.append(pages.Page(embeds=[embed]))

    # Include Continuum Images within Embed Pages
    continuum_images = await generate_paginated_continuum_images(continuum_badges)
    file_chunks = [continuum_images[i:i + 10] for i in range(0, len(continuum_images), 10)]
    for chunk in file_chunks:
      for file in chunk:
        continuum_page = pages.Page(
          embeds=[
            discord.Embed(
              color=discord.Color.dark_gold()
            ).set_image(url=f"attachment://{file.filename}")
          ],
          files=[file]
        )
        tongo_pages.append(continuum_page)

    # Send Risk Details as Paginator
    continuum_paginator = TongoPaginator(
      pages=tongo_pages,
      show_indicator=True,
      custom_buttons=self.tongo_buttons,
      use_default_buttons=False,
      timeout=300
    )
    await continuum_paginator.respond(ctx.interaction, ephemeral=False)

    # Potentially trigger a Consortium post-join
    all_players = await db_get_players_for_game(game['id'])
    if len(all_players) >= 5 and random.random() < 0.2:
      consortium_result = await self._find_consortium_badge_to_add(game['id'])
      if consortium_result:
        badge_info_id, prestige_level = consortium_result
        await self._invoke_zek_consortium(badge_info_id, prestige_level, game_id=game['id'])

    if confront_needed:
      await self._trigger_necessary_autoconfront("risk")


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

  async def _find_consortium_badge_to_add(self, game_id: int) -> Optional[tuple[int, int]]:
    """
    Attempts to find a badge_info_id and prestige_level pair that:
      - Appears on the wishlists of 3 or more players at the same prestige level
      - Does not already exist in the tongo_continuum at that badge_info_id + prestige_level
      - Is not a Special badge
      - Has not already received a consortium toss at that prestige level this game

    Returns:
      (badge_info_id, prestige_level) or None
    """
    # Get all continuum entries currently in play
    existing_by_prestige = await db_get_grouped_continuum_badge_info_ids_by_prestige()

    # Get all players in the game
    players = await db_get_players_for_game(game_id)

    # Get Special badge IDs to exclude
    special_badge_ids = {b['id'] for b in await db_get_special_badge_info()}

    # Track wishlist counts by (badge_info_id, prestige_level)
    combo_counts = defaultdict(int)

    for p in players:
      user_id = p['user_discord_id']
      echelon = await db_get_echelon_progress(user_id)
      prestige = echelon['current_prestige_tier'] if echelon else 0

      if prestige in await db_get_consortium_tiers_for_game(game_id):
        continue  # already granted consortium at this tier

      wants = await db_get_active_wants(user_id, prestige)
      if len(wants) < MINIMUM_AVARICE_QUOTIENT:
        continue

      for w in wants:
        key = (w['badge_info_id'], prestige)
        if key not in existing_by_prestige and w['badge_info_id'] not in special_badge_ids:
          combo_counts[key] += 1

    # Randomly choose one eligible (badge_info_id, prestige_level) pair among those wishlisted by at least users
    eligible = [(bid, prestige) for (bid, prestige), count in combo_counts.items() if count >= 3]
    if not eligible:
      return None

    return random.choice(eligible)


  async def _invoke_zek_consortium(self, badge_info_id: int, prestige_level: int, game_id: int):
    # Create a Consortium Reward with specified prestige level
    instance = await create_new_badge_instance(None, badge_info_id, prestige_level=prestige_level, event_type="tongo_consortium_investment")
    await db_add_to_continuum(instance['badge_instance_id'], None, game_id=game_id, via_consortium=True)

    consortium_embed = discord.Embed(
      title=f"A *{PRESTIGE_TIERS[prestige_level]} Consortium* has been formed!",
      description=(
        "Behind closed doors and beneath banners of profit, Grand Nagus Zek has arranged a **Consortium Investment Opportunity**.\n\n"
        f"An exceedingly coveted **{instance['badge_name']} [{PRESTIGE_TIERS[prestige_level]}]** has been quietly slipped into the Great Material Continuum.\n\n"
        "Rumors suggest... at least *three players* had their lobes set on this prize. "
        "Naturally, Brunt is outraged."
      ),
      color=discord.Color.gold()
    )
    consortium_embed.set_footer(text="Greed is Eternal", icon_url="https://i.imgur.com/scVHPNm.png")
    consortium_embed.set_image(url="https://i.imgur.com/hkVUsvQ.gif")

    main_color_tuple = discord.Color.gold().to_rgb()
    badge_frames = await generate_singular_badge_slot(instance, border_color=main_color_tuple)

    if len(badge_frames) > 1:
      buf = await encode_webp(badge_frames)
      discord_file = discord.File(buf, filename='consortium_badge.webp')
    else:
      discord_file = buffer_image_to_discord_file(badge_frames[0], 'consortium_badge.png')

    investment_embed = discord.Embed(
      title=f"{instance['badge_name']} [{PRESTIGE_TIERS[prestige_level]}]",
      color=discord.Color.gold()
    )
    investment_embed.set_image(url=f"attachment://{discord_file.filename}")

    zeks_table = await self.bot.fetch_channel(get_channel_id("zeks-table"))
    await zeks_table.send(embeds=[consortium_embed, investment_embed], files=[discord_file])


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

    # Ensure that the piece-of-shit timer is running or if we need to confront the damn game if it's expired somehow
    confront_needed = await self._ensure_auto_confront_active_or_confront_needed("index")

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
    tongo_continuum_badges = await db_get_full_continuum_badges()
    tongo_continuum_chunks = [tongo_continuum_badges[i:i + 20] for i in range(0, len(tongo_continuum_badges), 20)]

    description = f"Index requested by **{edf(user_member.display_name)}**! Displaying the status of the current game of Tongo!"
    if self.auto_confront.next_iteration:
      description += f"\n\nThis Tongo game will confront {humanize.naturaltime(self.auto_confront.next_iteration)}."

    # First embed
    confirmation_embed = discord.Embed(
      title="TONGO! Call For Index!",
      description=description,
      color=discord.Color.dark_purple()
    )
    confirmation_embed.add_field(
      name="Tongo Chair",
      value=f"* {edf(active_chair_member.display_name)}",
      inline=False
    )
    confirmation_embed.add_field(
      name="Current Players",
      value="\n".join([f"* {m.display_name}" for m in tongo_player_members]),
      inline=False
    )
    confirmation_embed.add_field(
      name="The Great Material Continuum",
      value=f"{len(tongo_continuum_badges)} Total Badges\n-# See following pages for details!",
      inline=False
    )
    confirmation_embed.set_image(url="https://i.imgur.com/aWLYGKQ.gif")
    confirmation_embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
      icon_url="https://i.imgur.com/GTN4gQG.jpg"
    )

    tongo_pages = [pages.Page(embeds=[confirmation_embed])]
    for page_idx, t_chunk in enumerate(tongo_continuum_chunks):
      embed = discord.Embed(
        title=f"The Great Material Continuum (Page {page_idx + 1} of {len(tongo_continuum_chunks)})",
        color=discord.Color.dark_purple()
      )
      embed.add_field(
        name="Total Badges in the Continuum!",
        value="\n".join([f"* {b['badge_name']} [{PRESTIGE_TIERS[b['prestige_level']]}]" for b in t_chunk]),
        inline=False
      )
      embed.set_footer(
        text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
        icon_url="https://i.imgur.com/GTN4gQG.jpg"
      )
      tongo_pages.append(pages.Page(embeds=[embed]))

    # Send Continuum Badges as Paginator
    continuum_paginator = TongoPaginator(
      pages=tongo_pages,
      show_indicator=True,
      custom_buttons=self.tongo_buttons,
      use_default_buttons=False,
      timeout=300
    )
    await continuum_paginator.respond(ctx.interaction, ephemeral=False)

    # Continuum image display
    continuum_images = await generate_paginated_continuum_images(tongo_continuum_badges)
    zeks_table = await self.bot.fetch_channel(get_channel_id("zeks-table"))
    await send_continuum_images_to_channel(zeks_table, continuum_images)

    if confront_needed:
      await self._trigger_necessary_autoconfront("index")

  @tongo.command(
    name="dividends",
    description="View and Redeem your Tongo Dividends!"
  )
  @commands.check(access_check)
  async def dividends(self, ctx):
    await ctx.defer(ephemeral=True)
    user_id = ctx.author.id

    record = await db_get_tongo_dividends(user_id)
    balance = record['current_balance'] if record else 0
    lifetime = record['lifetime_earned'] if record else 0

    if balance == 0 and lifetime == 0:
      await ctx.followup.send(
        embed=discord.Embed(
          title="You Haven't Earned Any Dividends Yet!",
          description="Your avarice is insufficient! Get out there and play some Tongo to earn and redeem Dividends!",
          color=discord.Color.red()
        )
      )
      return

    embed = discord.Embed(
      title="Tongo Dividends",
      description=f"Your devotion to Ferengi Principles and the 285 Rules of Acquisition have earned you favor from Grand Nagus Zek.\n"
                  f"### Current Balance\n**{balance}** Dividends\n"
                  f"### Lifetime Earned\n**{lifetime}** Dividends\n\n"
                  "Each Tongo game you participate in earns you *one* Dividend and there are three possible Dividend Rewards...",
      color=discord.Color.gold()
    )
    embed.set_image(url="https://i.imgur.com/UjZkGLf.gif")
    embed.add_field(
      name="Dividend Exchange Rate",
      value="\n".join([
        f"* {reward['label']} — **{reward['cost']}** Dividends" for reward in DIVIDEND_REWARDS.values()
      ]),
      inline=False
    )
    embed.add_field(name=f"{DIVIDEND_REWARDS['buffer']['label']}", value="A Pattern Buffer you may use in the regular Starfleet Crystal Replicator.", inline=False)
    embed.add_field(name=f"{DIVIDEND_REWARDS['wishlist']['label']}", value="An immediate Wishlist Endowment courtesy of Grand Nagus Zek.", inline=False)
    embed.add_field(name=f"{DIVIDEND_REWARDS['replication']['label']}", value="The Materialization of a Guaranteed Rare(*+?*) Crystal via a delicious Ferengi Honeystick.", inline=False)
    embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
      icon_url="https://i.imgur.com/GTN4gQG.jpg"
    )

    await ctx.followup.send(embed=embed, view=TongoDividendsView(self, balance), ephemeral=True)


  #    ___       __           _____          ___              __
  #   / _ |__ __/ /____  ____/ ___/__  ___  / _/______  ___  / /_
  #  / __ / // / __/ _ \/___/ /__/ _ \/ _ \/ _/ __/ _ \/ _ \/ __/
  # /_/ |_\_,_/\__/\___/    \___/\___/_//_/_//_/  \___/_//_/\__/
  @tasks.loop(hours=6)
  async def auto_confront(self):
    try:
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
        self.auto_confront.cancel()
        self.first_auto_confront = True
        return

      await self._perform_confront(active_tongo, active_chair)
      self.auto_confront.cancel()
      self.first_auto_confront = True
    except Exception as e:
      log_manual_exception(e, 'auto_confront error')

  async def _perform_confront(self, active_tongo, active_chair):
    try:
      players = await db_get_players_for_game(active_tongo['id'])
      player_ids = [int(p['user_discord_id']) for p in players]
      liquidation_result = None

      # Build wishlist snapshots before any transfer take place
      wishlist_snapshots = {}
      for p in players:
        user_id = int(p['user_discord_id'])
        raw_wishlist = await db_get_simple_wishlist_badges(user_id)
        wishlist_filenames = {b['badge_filename'] for b in raw_wishlist}
        wishlist_snapshots[user_id] = wishlist_filenames

      # Execute the transfers
      player_distribution = await self._execute_confront_distribution(active_tongo['id'], player_ids)
      remaining_badges = await db_get_full_continuum_badges()
      # Execute potential liquidation
      try:
        liquidation_result = await self._handle_liquidation(active_tongo['id'], remaining_badges, player_ids)
      except Exception as e:
        liquidation_result = None
        log_manual_exception(e, 'Liquidation Error')
        pass
      # Executions complete, mark game as resolved
      await db_update_game_status(active_tongo['id'], 'resolved')

      # Send main channel results embed
      results_embeds = await build_confront_results_embeds(active_chair, remaining_badges)
      zeks_table = await self.bot.fetch_channel(get_channel_id("zeks-table"))

      channel_message = None
      if len(results_embeds) > 0:
        continuum_paginator = TongoPaginator(
          pages=results_embeds,
          show_indicator=True,
          custom_buttons=self.tongo_buttons,
          use_default_buttons=False,
          timeout=300,
          author_check=False
        )
        channel_message = await zeks_table.send(embed=continuum_paginator.pages[0], view=continuum_paginator)
        continuum_paginator.message = channel_message
        await continuum_paginator.edit(channel_message) # Replace contents of the message with the actual Paginator

      # Send per-player results embeds
      for user_id, badge_instance_ids in player_distribution.items():
        member = await self.bot.current_guild.fetch_member(user_id)

        if badge_instance_ids:
          badges_received = [
            await db_get_badge_instance_by_id(instance_id)
            for instance_id in badge_instance_ids
          ]
          wishlist_filenames = wishlist_snapshots.get(user_id, set())
          wishlist_filenames_received = [
            b['badge_filename'] for b in badges_received if b['badge_filename'] in wishlist_filenames
          ]

          received_image, received_image_url = await generate_badge_trade_images(
            badges_received,
            f"Badges Won By {member.display_name}",
            f"{len(badges_received)} Badges"
          )

          dividends_rewarded = 0
          if len(badge_instance_ids) < 3:
            dividends_rewarded = 3 - len(badge_instance_ids)
            await db_increment_tongo_dividends(user_id, amount=dividends_rewarded)

          player_embed = await build_confront_player_embed(member, badges_received, wishlist_filenames_received, dividends_rewarded)
          player_embed.set_image(url=received_image_url)
          player_message = await zeks_table.send(embed=player_embed, file=received_image)

          jump_url = channel_message.jump_url if channel_message else player_message.jump_url
          dm_embed = build_confront_dm_embed(member, badges_received, wishlist_filenames_received, jump_url, dividends_rewarded)
          try:
            await member.send(embed=dm_embed)
          except discord.Forbidden:
            logger.info(f"Unable to DM {member.display_name} — DMs closed.")
        else:
          dividends_rewarded = 3
          await db_increment_tongo_dividends(user_id, amount=dividends_rewarded)

          channel_embed = build_confront_no_rewards_embed(member, dividends_rewarded)
          await zeks_table.send(embed=channel_embed)

          dm_embed = build_confront_dm_embed(member, [], [], channel_message.jump_url, dividends_rewarded)
          try:
            await member.send(embed=dm_embed)
          except discord.Forbidden:
            logger.info(f"Unable to DM {member.display_name} — DMs closed.")

      # Send liquidation results embeds (if a liquidation did in fact occur)
      if liquidation_result:
        member = await self.bot.current_guild.fetch_member(liquidation_result['beneficiary_id'])
        reward = liquidation_result['beneficiary_reward']
        removed = liquidation_result['tongo_badges_to_remove']

        # Main embed
        await zeks_table.send(embed=build_liquidation_embed(member, reward, removed))

        # Liquidated image
        removal_image, removal_image_url = await generate_badge_trade_images(removed, "Badges Liquidated", f"{len(removed)} Badges Liquidated")
        await zeks_table.send(embed=build_liquidation_removal_embed(removed, removal_image_url), file=removal_image)

        # Endowment image
        main_color_tuple = discord.Color.gold().to_rgb()
        badge_frames = await generate_singular_badge_slot(reward, border_color=main_color_tuple)

        endowment_file = None
        if len(badge_frames) > 1:
          # We might throw a crystallized one in here at some point?
          buf = await encode_webp(badge_frames)
          endowment_file = discord.File(buf, filename='liquidation_reward.webp')
        else:
          endowment_file = buffer_image_to_discord_file(badge_frames[0], 'liquidation_reward.png')

        endowment_embed = discord.Embed(
          title=f"{member.display_name}'s Liquidation Endowment",
          description=f"## {reward['badge_name']} [{PRESTIGE_TIERS[reward['prestige_level']]}]",
          color=discord.Color.gold()
        )
        endowment_embed.set_image(url=f"attachment://{endowment_file.filename}")
        await zeks_table.send(embed=endowment_embed, file=endowment_file)

        # DM
        try:
          await member.send(embed=build_liquidation_dm_embed(member, reward))
        except discord.Forbidden:
          logger.info(f"Unable to DM {member.display_name} about liquidation — DMs closed.")

      # Refresh final continuum and send images to channel
      updated = await db_get_full_continuum_badges()
      if updated:
        images = await generate_paginated_continuum_images(updated)
        await send_continuum_images_to_channel(zeks_table, images)
    except Exception as e:
      logger.exception("Unhandled exception in Tongo _perform_confront")
      log_manual_exception(e, "Unhandled exception in Tongo _perform_confront")

  async def _execute_confront_distribution(self, game_id: int, player_ids: list[dict]) -> dict[int, set[int]]:
    continuum_records = await db_get_full_continuum_badges()
    if not continuum_records:
      return {}

    continuum_distribution: set[int] = set()
    player_distribution: dict[int, set[int]] = {pid: set() for pid in player_ids}
    player_inventories: dict[int, dict[int, set[int]]] = {}  # {player_id: {prestige_level: set(info_ids)}}
    player_wishlists: dict[int, set[int]] = {}
    player_prestige: dict[int, int] = {}

    # Build inventory, active wants (wishlist), and prestige data
    for player_id in player_ids:
      # Prestige
      echelon_progress = await db_get_echelon_progress(player_id)
      prestige = echelon_progress['current_prestige_tier'] if echelon_progress else 0
      player_prestige[player_id] = prestige

      # Full inventory across all prestiges (*explictly* pass `prestige=None` here to get all badges at ALL prestiges)
      inventory = await db_get_user_badge_instances(player_id, prestige=None)
      prestige_inventory: dict[int, set[int]] = defaultdict(set)
      for item in inventory:
        prestige_inventory[item['prestige_level']].add(item['badge_info_id'])
      player_inventories[player_id] = prestige_inventory

      # Wishlist for *current* prestige only
      active_wants = await db_get_active_wants(player_id, prestige)
      wishlist_info_ids = set(b['badge_info_id'] for b in active_wants)
      player_wishlists[player_id] = wishlist_info_ids

    # Shuffle the deck
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
        badge_prestige = badge['prestige_level']
        if badge_prestige > prestige_limit:
          continue

        info_id = badge['badge_info_id']
        owned_at_this_prestige = info_id in player_inventories[current_player].get(badge_prestige, set())
        wishlist = player_wishlists[current_player]

        if owned_at_this_prestige:
          continue

        if info_id in wishlist:
          selected_badge = badge
          break

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

    # Assign badges atomically and record rewards
    success = await self.transfer_all_tongo_rewards(game_id, player_distribution)
    if not success:
      # Sad Trombone Noises
      await db_update_game_status(game_id, 'error')
      maintainer = await self.bot.current_guild.fetch_member(config["maintainer_user_id"])
      await maintainer.send(embed=discord.Embed(title="Tongo Blew Up...", description="Check the logs.", color=discord.Color.red()))
      failure_embed = discord.Embed(
        title="Please Stand By",
        description="Tongo is suffering Technical Difficulties.\n\nNew game creation has been temporarily disabled and the proper authorities have been notified...",
        color=discord.Color.red()
      )
      failure_embed.set_image(url="https://i.imgur.com/jkm7cnA.gif")
      zeks_table = await self.cog.bot.fetch_channel(get_channel_id("zeks-table"))
      await zeks_table.send(embed=failure_embed)
      raise RuntimeError("Tongo reward transfer failed, transaction rolled back")

    return player_distribution


  async def transfer_all_tongo_rewards(self, game_id: int, player_distribution: dict[int, set[int]]) -> bool:
    """
    Transfers all Tongo rewards to players in a single transaction.
    Rolls back everything if any one transfer fails.

    Args:
      game_id (int): ID of the Tongo game
      player_distribution (dict): Mapping of user_id -> set of badge_instance_ids

    Returns:
      bool: True if successful, False if any failure occurred
    """
    async with AgimusTransactionDB(dictionary=True) as db:
      try:
        await db.begin()

        for player_user_id, instance_ids in player_distribution.items():
          for instance_id in instance_ids:
            # Fetch instance and validate
            await db.execute("SELECT owner_discord_id, badge_info_id, prestige_level FROM badge_instances WHERE id = %s", (instance_id,))
            row = await db.fetchone()

            if not row:
              logger.error(f"[TONGO] Failed to fetch badge instance {instance_id}")
              raise RuntimeError("Badge instance missing")

            from_user_id = row['owner_discord_id']
            badge_info_id = row['badge_info_id']
            prestige_level = row['prestige_level']

            if from_user_id == player_user_id:
              logger.warning(f"[TONGO] Instance {instance_id} already owned by {player_user_id}.")
              raise RuntimeError("Instance already owned by user")

            # Ensure user doesn't already own this badge_info_id at this prestige
            await db.execute("""
              SELECT 1 FROM badge_instances
              WHERE owner_discord_id = %s AND badge_info_id = %s AND prestige_level = %s AND active = TRUE
            """, (player_user_id, badge_info_id, prestige_level))
            if await db.fetchone():
              logger.warning(f"[TONGO] User {player_user_id} already owns badge_info_id {badge_info_id} at prestige {prestige_level}.")
              raise RuntimeError("Duplicate badge assignment")

            # Perform transfer
            await db.execute(
              "UPDATE badge_instances SET owner_discord_id = %s, locked = FALSE WHERE id = %s",
              (player_user_id, instance_id)
            )

            await db.execute(
              """
              INSERT INTO badge_instance_history (badge_instance_id, from_user_id, to_user_id, event_type)
              VALUES (%s, %s, %s, 'tongo_reward')
              """,
              (instance_id, from_user_id, player_user_id)
            )

            await db.execute(
              "DELETE FROM tongo_continuum WHERE source_instance_id = %s",
              (instance_id,)
            )

            await db.execute(
              """
              INSERT IGNORE INTO tongo_game_rewards (game_id, user_discord_id, badge_instance_id)
              VALUES (%s, %s, %s)
              """,
              (game_id, player_user_id, instance_id)
            )

            # Check if badge is on the player's wishlist and lock it if so
            await db.execute("""
              SELECT 1 FROM badge_instances_wishlists
              WHERE user_discord_id = %s AND badge_info_id = %s
            """, (player_user_id, badge_info_id))
            if await db.fetchone():
              await db.execute("UPDATE badge_instances SET locked = TRUE WHERE id = %s", (instance_id,))

        await db.commit()
        return True

      except Exception as e:
        await db.rollback()
        logger.exception("[TONGO] Transaction rollback during multi-reward transfer")
        log_manual_exception(e, "TONGO multi-reward failure")
        return False


  async def _handle_liquidation(self, game_id: int, tongo_continuum: list[dict], player_ids: list[int]) -> Optional[dict]:
    if len(tongo_continuum) < MINIMUM_LIQUIDATION_CONTINUUM or len(player_ids) < MINIMUM_LIQUIDATION_PLAYERS:
      return None

    if random.random() > 0.33:
      return None

    liquidation_result = await self._determine_liquidation(tongo_continuum, player_ids, game_id)
    if not liquidation_result:
      return None

    badge_to_grant = liquidation_result['badge_to_grant']
    badge_info_id = badge_to_grant['badge_info_id']
    prestige_level = badge_to_grant['prestige_level']
    beneficiary_id = liquidation_result['beneficiary_id']

    # Create a new instance using utility helper that tracks origin reason
    reward_instance = await create_new_badge_instance(beneficiary_id, badge_info_id, prestige_level=prestige_level, event_type='liquidation_endowment')
    if not reward_instance:
      return None
    liquidation_result['beneficiary_reward'] = reward_instance
    await db_add_game_reward(game_id, beneficiary_id, reward_instance['badge_instance_id'])

    # Liquidate the selected badges
    for badge in liquidation_result['tongo_badges_to_remove']:
      await db_remove_from_continuum(badge['source_instance_id'])
      await liquidate_badge_instance(badge['source_instance_id'])

    return liquidation_result


  async def _determine_liquidation(self, continuum: list[dict], tongo_players: list[int], game_id: int) -> Optional[dict]:
    players = tongo_players.copy()
    random.shuffle(players)

    for player_id in players:
      echelon_progress = await db_get_echelon_progress(player_id)
      prestige = echelon_progress['current_prestige_tier'] if echelon_progress else 0
      active_wants = await db_get_active_wants(player_id, prestige)

      inventory = await db_get_user_badge_instances(player_id, prestige=None)
      owned_pairs = {(b['badge_info_id'], b['prestige_level']) for b in inventory}
      wishlist_to_grant = [
        b for b in active_wants
        if (b['badge_info_id'], prestige) not in owned_pairs
      ]

      if not wishlist_to_grant or len(wishlist_to_grant) < MINIMUM_AVARICE_QUOTIENT / 3:
        continue

      random.shuffle(wishlist_to_grant)
      badge_to_grant = wishlist_to_grant[0]
      badge_to_grant['prestige_level'] = prestige

      # Protect consortium-tossed badges from liquidation if they were added in the last 3 games
      recent_game_ids = await db_get_last_n_game_ids(3)
      available_badges = [
        b for b in continuum
        if not (b.get('added_via_consortium') and b.get('game_id') in recent_game_ids)
      ]
      random.shuffle(available_badges)
      badges_to_remove = available_badges[:3]

      liquidation_result = {
        'beneficiary_id': player_id,
        'badge_to_grant': badge_to_grant,
        'tongo_badges_to_remove': badges_to_remove
      }

      return liquidation_result

    return None


  # ___________      .__.__                  _____
  # \_   _____/____  |__|  |   ___________ _/ ____\____
  #  |    __) \__  \ |  |  |  /  ___/\__  \\   __\/ __ \
  #  |     \   / __ \|  |  |__\___ \  / __ \|  | \  ___/
  #  \___  /  (____  /__|____/____  >(____  /__|  \___  >
  #      \/        \/             \/      \/          \/
  async def _ensure_auto_confront_active_or_confront_needed(self, source: str):
    """
    Going full nuclear on this goddamn thing.

    Ensures that the auto_confront timer is running if a game is active.
    If time has already elapsed, it triggers confrontation immediately.
    Used to prevent the timer from being lost due to reboots, or runtime errors,
    or whatever mysterious bullshit keeps happening that has thus-far been untraceable.

    Args:
      source: "reboot", "index", or "risk" — for messaging context
      silent: suppresses output if True (e.g. from /tongo risk)
    """
    active_tongo = await db_get_open_game()
    if not active_tongo:
      return False

    if self.auto_confront.next_iteration is not None:
      # Timer is already running — no need to do anything
      return False

    try:
      chair_id = int(active_tongo['chair_user_id'])
      chair = await self.bot.current_guild.fetch_member(chair_id)
      zeks_table = await self.bot.fetch_channel(get_channel_id("zeks-table"))
    except Exception as e:
      logger.warning(f"Failed to recover Tongo game state: {e}")
      return False

    # Ensure UTC timezone
    time_created = active_tongo['created_at']
    if time_created.tzinfo is None:
      time_created = time_created.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    elapsed = now - time_created
    remaining = TONGO_AUTO_CONFRONT_TIMEOUT - elapsed

    if remaining.total_seconds() <= 0:
      # True because we need to actually confront the fucking thing
      return True
    else:
      # Still time left, just restart the timer
      if self.auto_confront.is_running():
        self.auto_confront.cancel()
      self.first_auto_confront = True
      self.auto_confront.change_interval(seconds=remaining.total_seconds())
      self.auto_confront.start()

      if source == "reboot":
        # Only give an indication that we recovered,
        # and lock out further consortium activations (since we don't know prior state),
        # if the source is a true reboot where we've lost the in-memory flag...
        embed = discord.Embed(
          title="REBOOT DETECTED! Resuming Tongo...",
          description="We had a game in progress! ***Rude!***\n\n"
                      f"The current game started by **{chair.display_name}** has been resumed.\n\n"
                      f"This Tongo game has {humanize.naturaltime(now + remaining)} left before it ends!",
          color=discord.Color.red()
        )
        embed.set_image(url="https://i.imgur.com/K4hUjh6.gif")
        embed.set_footer(
          text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
          icon_url="https://i.imgur.com/GTN4gQG.jpg"
        )
        await zeks_table.send(embed=embed)
      elif source in ("index", "risk"):
        # Otherwise just log the recovery and play non-chalant while whistling with hands in pockets...
        logger.info(f"Tongo timer recovered from {source}: {remaining.total_seconds()}s remaining.")

      # No auto-confront triggered, we're safe to return False
      return False

  async def _trigger_necessary_autoconfront(self, source: str):
    # Apparently the timer expired, trigger the goddamn confrontation ourselves...
    active_tongo = await db_get_open_game()
    if not active_tongo:
      logger.error("We somehow got into a _trigger_necessary_autoconfront() without an active game... ???")
      return

    try:
      chair_id = int(active_tongo['chair_user_id'])
      chair = await self.bot.current_guild.fetch_member(chair_id)
      zeks_table = await self.bot.fetch_channel(get_channel_id("zeks-table"))
    except Exception as e:
      logger.warning(f"Failed to recover Tongo game state: {e}")
      return False

    title = "DOWNTIME DETECTED! Confronting Tongo..." if source == "reboot" else "Timer Expired! Confronting..."
    embed = discord.Embed(
      title=title,
      description=f"**Heywaitaminute!!!** The game started by **{chair.display_name}** never confronted in time. Confronting now!",
      color=discord.Color.red()
    )
    embed.set_image(url="https://i.imgur.com/t5dZu6O.gif")
    embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
      icon_url="https://i.imgur.com/GTN4gQG.jpg"
    )
    await zeks_table.send(embed=embed)

    await self._perform_confront(active_tongo, chair)
    if self.auto_confront.is_running():
      self.auto_confront.cancel()
    self.first_auto_confront = True

  # __________        _____
  # \______   \ _____/ ____\___________   ____   ____
  #  |       _// __ \   __\/ __ \_  __ \_/ __ \_/ __ \
  #  |    |   \  ___/|  | \  ___/|  | \/\  ___/\  ___/
  #  |____|_  /\___  >__|  \___  >__|    \___  >\___  >
  #         \/     \/          \/            \/     \/
  tongo_referee_group = discord.SlashCommandGroup("referee", "Referee commands for Tongo.")

  @tongo_referee_group.command(name="toggle_block_tongo", description="(ADMIN RESTRICTED) Enable or disable Tongo games.")
  @commands.check(user_check)
  async def toggle_block_tongo(self, ctx: discord.ApplicationContext, block: bool):
    self.block_new_games = block
    await db_set_tongo_block_new_games(block)
    await ctx.respond(
      embed=discord.Embed(
        title="Tongo Game Blocking Updated",
        description=f"New games are now {'blocked' if block else 'allowed'}.",
        color=discord.Color.blurple()
      ),
      ephemeral=True
    )

  @tongo_referee_group.command(name="confront_tongo_game", description="(ADMIN RESTRICTED) Force Confrontation of the current Tongo game.")
  @commands.check(user_check)
  async def confront_tongo_game(self, ctx):
    await ctx.defer(ephemeral=True)

    active_game = await db_get_open_game()
    if not active_game:
      return await ctx.respond(embed=discord.Embed(
        title="No Active Tongo Game",
        description="There is currently no open Tongo game to confront.",
        color=discord.Color.red()
      ), ephemeral=True)

    try:
      chair = await self.bot.current_guild.fetch_member(int(active_game['chair_user_id']))
    except Exception as e:
      logger.warning(f"Could not fetch Tongo chair user: {e}")
      return await ctx.respond(embed=discord.Embed(
        title="Failed to Confront",
        description="Could not fetch the chair for the current game. Check user ID validity.",
        color=discord.Color.red()
      ), ephemeral=True)

    await self._perform_confront(active_game, chair)
    self.auto_confront.cancel()
    self.first_auto_confront = True

    await ctx.respond(embed=discord.Embed(
      title="Tongo Game Confronted!",
      description=f"The current game chaired by {chair.display_name} has been forcefully ended and resolved.",
      color=discord.Color.gold()
    ), ephemeral=True)

  # @tongo_referee_group.command(
  #   name="zek_investment",
  #   description="(ADMIN RESTRICTED) Have Zek make things extra spicy."
  # )
  # @commands.check(user_check)
  # async def zek_investment(self, ctx: discord.ApplicationContext):
  #   await ctx.defer(ephemeral=True)

  #   game = await db_get_open_game()
  #   if not game:
  #     return await ctx.respond(embed=discord.Embed(
  #       title="No Active Tongo Game",
  #       description="There is no ongoing Tongo game to add a Consortium badge to!",
  #       color=discord.Color.red()
  #     ), ephemeral=True)

  #   self.zek_consortium_activated = False

  #   result = await self._find_consortium_badge_to_add(game['id'])
  #   if not result:
  #     return await ctx.respond(embed=discord.Embed(
  #       title="No Eligible Consortium Badge",
  #       description="There is no badge that 3 or more players want at a shared prestige level.",
  #       color=discord.Color.red()
  #     ), ephemeral=True)

  #   badge_info_id, prestige = result
  #   await self._invoke_zek_consortium(badge_info_id, prestige)
  #   self.zek_consortium_activated = True

  #   await ctx.respond(embed=discord.Embed(
  #     title="Consortium Toss Complete",
  #     description="A badge has been thrown into the Continuum by Grand Nagus Zek.",
  #     color=discord.Color.gold()
  #   ), ephemeral=True)


#
# UTILS
#
async def throw_badge_into_continuum(instance, user_id, current_game_id):
  """
  Utility to place a badge into the continuum and, importantly, revoke the current user's ownership
  """
  await db_add_to_continuum(instance['badge_instance_id'], user_id, game_id=current_game_id, via_consortium=False)
  await transfer_badge_instance(instance['badge_instance_id'], None, 'tongo_risk')


async def send_continuum_images_to_channel(trade_channel, continuum_images):
  # We can only attach up to 10 files per message, so send them in chunks if needed
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
async def build_confront_results_embeds(active_chair: discord.Member, remaining_badges: list[dict]) -> list[discord.Embed]:
  title = "TONGO! Complete!"
  description= "Distributing Badges from The Great Material Continuum!"

  embeds = []

  first_embed = discord.Embed(
    title=title,
    description=description,
    color=discord.Color.dark_purple()
  )
  first_embed.set_image(url="https://i.imgur.com/gdpvba5.gif")
  first_embed.set_footer(
    text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
    icon_url="https://i.imgur.com/GTN4gQG.jpg"
  )

  if remaining_badges:
    if len(remaining_badges) < 20:
      if remaining_badges:
        first_embed.add_field(
          name="Remaining Badges In The Great Material Continuum!",
          value="\n".join([f"* {b['badge_name']} [{PRESTIGE_TIERS[b['prestige_level']]}]" for b in remaining_badges]),
          inline=False
        )
      embeds.append(first_embed)
    else:
      embeds.append(first_embed)
      # Chunk the continuum into 20-badge chunks
      continuum_chunks = [remaining_badges[i:i + 20] for i in range(0, len(remaining_badges), 20)]
      for page_idx, t_chunk in enumerate(continuum_chunks):
        embed = discord.Embed(
          title=f"The Great Material Continuum (Page {page_idx + 1} of {len(continuum_chunks)})",
          color=discord.Color.dark_purple()
        )
        embed.add_field(
          name="Remaining Badges in the Continuum!",
          value="\n".join([f"* {b['badge_name']} [{PRESTIGE_TIERS[b['prestige_level']]}]" for b in t_chunk]),
          inline=False
        )
        embed.set_footer(
          text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
          icon_url="https://i.imgur.com/GTN4gQG.jpg"
        )
        embeds.append(embed)

  return embeds

async def build_confront_player_embed(member: discord.Member, badge_infos: list[dict], wishlist_badge_filenames: list[str], dividends_rewarded: int = 0) -> discord.Embed:
  description = ""
  if dividends_rewarded:
    description = f"\n\nOops, sorry {member.mention}... they got back less than they put in!\n\nOn the bright side they've been awarded **{dividends_rewarded} Tongo Dividend{'s' if dividends_rewarded > 1 else ''}** as a consolation prize!\n"

  description += "### Distributed\n"
  description += "\n".join([
    f"* {b['badge_name']} [{PRESTIGE_TIERS[b['prestige_level']]}] {' ✨' if b['badge_filename'] in wishlist_badge_filenames else ''}"
    for b in badge_infos
  ])

  embed = discord.Embed(
    title=f"{edf(member.display_name)}'s Results:",
    description=description,
    color=discord.Color.dark_purple()
  )
  if wishlist_badge_filenames:
    embed.set_footer(text="✨ - Indicates a wishlist badge!")

  return embed


def build_confront_dm_embed(member: discord.Member, badge_infos: list[dict], wishlist_badge_filenames: list[str], jump_url: str, dividends_rewarded: int = 0) -> discord.Embed:
  title = "TONGO! Confront!"
  description= f"Heya {edf(member.display_name)}! Your Tongo game has ended!"

  if dividends_rewarded:
    description+= f"\n\nOops, you received fewer than 3 badges — so you've been awarded **{dividends_rewarded} Dividend{'s' if dividends_rewarded > 1 else ''}** as a consolation prize, and can view the full game results at: {jump_url}"
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
        f"* {b['badge_name']} [{PRESTIGE_TIERS[b['prestige_level']]}]{' ✨' if b['badge_filename'] in wishlist_badge_filenames else ''}"
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


def build_confront_no_rewards_embed(member: discord.Member, dividends_rewarded: int) -> discord.Embed:
  embed = discord.Embed(
    title=f"{edf(member.display_name)} did not receive any badges...",
    description=f"but they've been awarded **{dividends_rewarded} Tongo Dividends** as a consolation prize!",
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
      f"✨ **{edf(member.display_name)}** is the *Lucky Liquidation Beneficiary*!!! ✨\n\n"
      "A deal is a deal... until a better one comes along!"
    ),
    color=discord.Color.gold()
  )

  embed.set_image(url="https://i.imgur.com/U9U0doQ.gif")

  embed.add_field(
    name=f"{edf(member.display_name)} receives a random badge they've been coveting...",
    value=f"* ✨ {reward_badge['badge_name']} [{PRESTIGE_TIERS[reward_badge['prestige_level']]}] ✨",
    inline=False
  )

  embed.add_field(
    name="Badges Liquidated from The Great Material Continuum",
    value="\n".join([f"* {b['badge_name']} [{PRESTIGE_TIERS[b['prestige_level']]}]" for b in removed_badges]),
    inline=False
  )

  embed.set_footer(
    text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
    icon_url="https://i.imgur.com/scVHPNm.png"
  )

  return embed

def build_liquidation_dm_embed(member: discord.Member, reward_badge: dict) -> discord.Embed:
  embed = discord.Embed(
    title="LIQUIDATION!",
    description=(
      f"Heya {edf(member.display_name)}, Grand Nagus Zek has decreed a Liquidation of The Great Material Continuum, "
      f"and as the ✨ *Lucky Liquidation Beneficiary* ✨ you have received a randomized badge from your wishlist!\n\n"
      "**Congratulations!**"
    ),
    color=discord.Color.gold()
  ).set_footer(text="Greed is Eternal!")

  embed.add_field(
    name="You received...",
    value=f"* ✨ {reward_badge['badge_name']} [{PRESTIGE_TIERS[reward_badge['prestige_level']]}] ✨"
  )

  return embed


def build_liquidation_endowment_embed(member: discord.Member, reward_image_url) -> discord.Embed:
  embed = discord.Embed(
    title="Liquidation Endowment",
    description=(
      f"As the ✨ *Lucky Liquidation Beneficiary* ✨ **{edf(member.display_name)}** has been granted a freshly-minted, randomized badge from their wishlist!"
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
async def generate_paginated_continuum_images(continuum_badges):
  from utils.image_utils import compose_badge_slot, buffer_image_to_discord_file, _get_badge_slot_dimensions

  dims = _get_badge_slot_dimensions()
  margin = 20
  items_per_page = 12
  pages = [continuum_badges[i:i + items_per_page] for i in range(0, len(continuum_badges), items_per_page)]
  total_pages = len(pages)
  total_badges = len(continuum_badges)
  results = []

  fonts = load_fonts(general_size=50)
  text_font = fonts.general

  slot_height = int(dims.slot_height // 2)
  slot_width = dims.slot_height

  for page_index, page_badges in enumerate(pages):
    canvas_w = 800
    canvas_h = 100 + ((slot_height + 10) * math.ceil(len(page_badges) / 4)) + 115
    base_image = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0))

    # Load header/footer/bg
    header = await threaded_image_open("./images/templates/tongo/continuum_header.png")
    row_bg = await threaded_image_open("./images/templates/tongo/continuum_bg.png")
    footer = await threaded_image_open("./images/templates/tongo/continuum_footer.png")

    base_image.paste(header, (0, 0))

    row_y = 100
    row_h = slot_height + 10
    rows = math.ceil(len(page_badges) / 4)
    for i in range(rows):
      base_image.paste(row_bg, (0, row_y + i * row_h))

    base_image.paste(footer, (0, row_y + rows * row_h))

    # Build slots
    badge_slots = []
    for badge in page_badges:
      badge_image = await get_cached_base_badge_canvas(badge['badge_filename'])
      slot_frames = compose_badge_slot(badge, get_theme_colors('gold'), badge_image, disable_overlays=True, resize=True)
      badge_slots.append(slot_frames[0])

    current_y = row_y + 5
    index = 0
    for row in range(rows):
      row_badges = badge_slots[index:index+4]
      total_row_w = len(row_badges) * (slot_width // 2) + (len(row_badges) - 1) * margin
      x = (canvas_w - total_row_w) // 2
      for slot in row_badges:
        base_image.paste(slot, (x, current_y), slot)
        x += (slot_width // 2) + margin
      current_y += row_h
      index += 4

    # Footer text
    footer_text = f"{total_badges} TOTAL"
    if total_pages > 1:
      footer_text += f" -- PAGE {page_index + 1:02} OF {total_pages:02}"

    draw = ImageDraw.Draw(base_image)
    draw.text((canvas_w // 2, canvas_h - 50), footer_text, font=text_font, fill="#FCCE67", anchor="mm")

    results.append(buffer_image_to_discord_file(base_image, f"continuum_page_{page_index + 1}.png"))

  return results