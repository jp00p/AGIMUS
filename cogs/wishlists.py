# cogs/wishlist.py

from common import *

from queries.badge_info import *
from queries.badge_instances import db_get_user_badge_instances
from queries.echelon_xp import db_get_echelon_progress
from queries.wishlists import *
from utils.badge_utils import autocomplete_selections
from utils.check_channel_access import access_check
from utils.image_utils import generate_unowned_badge_preview
from utils.prestige import PRESTIGE_TIERS, autocomplete_prestige_tiers, is_prestige_valid
from utils.string_utils import strip_bullshit


paginator_buttons = [
  pages.PaginatorButton("prev", label="    ⬅     ", style=discord.ButtonStyle.primary, row=1),
  pages.PaginatorButton(
    "page_indicator", style=discord.ButtonStyle.gray, disabled=True, row=1
  ),
  pages.PaginatorButton("next", label="     ➡    ", style=discord.ButtonStyle.primary, row=1),
]

#    _____          __                                     .__          __
#   /  _  \  __ ___/  |_  ____   ____  ____   _____ ______ |  |   _____/  |_  ____
#  /  /_\  \|  |  \   __\/  _ \_/ ___\/  _ \ /     \\____ \|  | _/ __ \   __\/ __ \
# /    |    \  |  /|  | (  <_> )  \__(  <_> )  Y Y  \  |_> >  |_\  ___/|  | \  ___/
# \____|__  /____/ |__|  \____/ \___  >____/|__|_|  /   __/|____/\___  >__|  \___  >
#         \/                        \/            \/|__|             \/          \/
async def add_autocomplete(ctx:discord.AutocompleteContext):
  user_id = ctx.interaction.user.id
  wishlist_badge_names = [b['badge_name'] for b in await db_get_simple_wishlist_badges(user_id)]
  special_badge_names = [b['badge_name'] for b in await db_get_special_badge_info()]
  excluded_names = set(special_badge_names + wishlist_badge_names)

  all_badges = await db_get_all_badge_info()
  filtered_badges = [b for b in all_badges if b['badge_name'] not in excluded_names]

  choices = [
    discord.OptionChoice(
      name=b['badge_name'],
      value=str(b['id'])
    )
    for b in filtered_badges if strip_bullshit(ctx.value.lower()) in strip_bullshit(b['badge_name'].lower())
  ]
  return choices

async def remove_autocomplete(ctx:discord.AutocompleteContext):
  user_id = ctx.interaction.user.id
  special_badge_names = [b['badge_name'] for b in await db_get_special_badge_info()]
  wishlisted_badges = await db_get_simple_wishlist_badges(user_id)

  filtered_badges = [b for b in wishlisted_badges if b['badge_name'] not in special_badge_names]

  choices = [
    discord.OptionChoice(
      name=b['badge_name'],
      value=str(b['badge_info_id'])
    )
    for b in filtered_badges if strip_bullshit(ctx.value.lower()) in strip_bullshit(b['badge_name'].lower())
  ]
  return choices

async def lock_autocomplete(ctx: discord.AutocompleteContext):
  user_id = ctx.interaction.user.id
  # fetch all of their active instances
  instances = await db_get_user_badge_instances(user_id)
  # dedupe by badge_info_id
  badge_ids = {inst['badge_info_id'] for inst in instances}
  choices: list[discord.OptionChoice] = []
  for bid in badge_ids:
    info = await db_get_badge_info_by_id(bid)
    # only show badges whose names match the current input
    if strip_bullshit(ctx.value.lower()) in strip_bullshit(info['badge_name'].lower()):
      choices.append(discord.OptionChoice(
        name=info['badge_name'],
        value=str(bid),
      ))
  return choices

async def unlock_autocomplete(ctx: discord.AutocompleteContext):
  user_id = ctx.interaction.user.id
  # fetch only the instances they’ve locked
  instances = await db_get_user_badge_instances(user_id, locked=True)
  badge_ids = {inst['badge_info_id'] for inst in instances}
  choices: list[discord.OptionChoice] = []
  for bid in badge_ids:
    info = await db_get_badge_info_by_id(bid)
    if strip_bullshit(ctx.value.lower()) in strip_bullshit(info['badge_name'].lower()):
      choices.append(discord.OptionChoice(
        name=info['badge_name'],
        value=str(bid),
      ))
  return choices


# __________                .__               __
# \______   \_____     ____ |__| ____ _____ _/  |_  ___________
#  |     ___/\__  \   / ___\|  |/    \\__  \\   __\/  _ \_  __ \
#  |    |     / __ \_/ /_/  >  |   |  \/ __ \|  | (  <_> )  | \/
#  |____|    (____  /\___  /|__|___|  (____  /__|  \____/|__|
#                 \//_____/         \/     \/
class WishlistPaginator(pages.Paginator):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

  async def on_timeout(self):
    try:
      await super().on_timeout()
    except discord.errors.NotFound as e:
      # Workaround for current issue with Paginator timeouts
      # If the interaction was edited or dismissed before the paginator timeout is reached
      # it encounters a 404 when it tries to load the original message to disable the UI elements
      # We're already done here at that point, so just go ahead and pass
      pass


# ________  .__               .__              __________        __    __
# \______ \ |__| ______ _____ |__| ______ _____\______   \__ ___/  |__/  |_  ____   ____
#  |    |  \|  |/  ___//     \|  |/  ___//  ___/|    |  _/  |  \   __\   __\/  _ \ /    \
#  |    `   \  |\___ \|  Y Y  \  |\___ \ \___ \ |    |   \  |  /|  |  |  | (  <_> )   |  \
# /_______  /__/____  >__|_|  /__/____  >____  >|______  /____/ |__|  |__|  \____/|___|  /
#         \/        \/      \/        \/     \/        \/                              \/
class DismissButton(discord.ui.Button):
  def __init__(
    self,
    cog,
    author_discord_id: str,
    match_discord_id: str,
    prestige_level: int,
    has_ids: list[int],
    wants_ids: list[int],
  ):
    super().__init__(label="Dismiss Match", style=discord.ButtonStyle.primary, row=2)
    self.cog               = cog
    self.author_discord_id = author_discord_id
    self.match_discord_id  = match_discord_id
    self.prestige_level    = prestige_level
    self.has_ids           = has_ids
    self.wants_ids         = wants_ids

  async def callback(self, interaction: discord.Interaction):
    await interaction.response.defer()
    # insert dismissal records per badge and role at this prestige
    for badge_id in self.has_ids:
      await db_add_wishlist_dismissal(
        self.author_discord_id,
        self.match_discord_id,
        badge_id,
        self.prestige_level,
        'has',
      )
    for badge_id in self.wants_ids:
      await db_add_wishlist_dismissal(
        self.author_discord_id,
        self.match_discord_id,
        badge_id,
        self.prestige_level,
        'wants',
      )

    match_user = await bot.current_guild.fetch_member(self.match_discord_id)
    await interaction.edit(
      embed=discord.Embed(
        title=f"Your wishlist match with {match_user.display_name} has been dismissed.",
        description="If new badges are found in the future the dismissal will be automatically cleared.",
        color=discord.Color.green()
      ),
      view=None
    )


# __________                   __          ________  .__               .__                      .__ __________        __    __
# \______   \ _______  ______ |  | __ ____ \______ \ |__| ______ _____ |__| ______ ___________  |  |\______   \__ ___/  |__/  |_  ____   ____
#  |       _// __ \  \/ /  _ \|  |/ // __ \ |    |  \|  |/  ___//     \|  |/  ___//  ___/\__  \ |  | |    |  _/  |  \   __\   __\/  _ \ /    \
#  |    |   \  ___/\   (  <_> )    <\  ___/ |    `   \  |\___ \|  Y Y  \  |\___ \ \___ \  / __ \|  |_|    |   \  |  /|  |  |  | (  <_> )   |  \
#  |____|_  /\___  >\_/ \____/|__|_ \\___  >_______  /__/____  >__|_|  /__/____  >____  >(____  /____/______  /____/ |__|  |__|  \____/|___|  /
#         \/     \/                \/    \/        \/        \/      \/        \/     \/      \/            \/                              \/
class RevokeDismissalButton(discord.ui.Button):
  def __init__(
    self,
    cog,
    author_discord_id: str,
    match_discord_id: str,
    prestige_level: int,
  ):
    super().__init__(label="Revoke Dismissal", style=discord.ButtonStyle.primary, row=2)
    self.cog               = cog
    self.author_discord_id = author_discord_id
    self.match_discord_id  = match_discord_id
    self.prestige_level    = prestige_level

  async def callback(self, interaction: discord.Interaction):
    await interaction.response.defer()
    # delete all dismissal rows for this user/match/prestige
    await db_delete_wishlist_dismissal(
      self.author_discord_id,
      self.match_discord_id,
      self.prestige_level,
    )
    match_user = await bot.current_guild.fetch_member(self.match_discord_id)
    await interaction.edit(
      embed=discord.Embed(
        title=f"Your dismissal of your wishlist match with {match_user.display_name} has been revoked.",
        description="You may use `/wishlist matches` to review the match now as well.",
        color=discord.Color.green()
      ),
      view=None
    )

#  __      __.__       .__    .__  .__          __    _________
# /  \    /  \__| _____|  |__ |  | |__| _______/  |_  \_   ___ \  ____   ____
# \   \/\/   /  |/  ___/  |  \|  | |  |/  ___/\   __\ /    \  \/ /  _ \ / ___\
#  \        /|  |\___ \|   Y  \  |_|  |\___ \  |  |   \     \___(  <_> ) /_/  >
#   \__/\  / |__/____  >___|  /____/__/____  > |__|    \______  /\____/\___  /
#        \/          \/     \/             \/                 \/      /_____/
class Wishlist(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  wishlist_group = discord.SlashCommandGroup("wishlist", "Badges Wishlist Commands!")

  @commands.Cog.listener()
  async def on_raw_reaction_add(self, payload):
    await self.handle_wishlist_reaction_toggle(payload)

  @commands.Cog.listener()
  async def on_raw_reaction_remove(self, payload):
    await self.handle_wishlist_reaction_toggle(payload)

  async def handle_wishlist_reaction_toggle(self, payload):
    if self.bot.user.id == payload.user_id:
      return
    if payload.channel_id != get_channel_id("badgeys-badges") or payload.emoji.name != "✅":
      return

    member = self.bot.current_guild.get_member(payload.user_id)
    if not member or member.bot:
      return

    user = await get_user(payload.user_id)
    channel = self.bot.get_channel(payload.channel_id)

    message = await channel.fetch_message(payload.message_id)
    if not message.embeds:
      return

    embed = message.embeds[0]
    if not embed.fields:
      return

    badge_name = embed.fields[0].name.strip()
    special = [b['badge_name'] for b in await db_get_special_badge_info()]
    if badge_name in special:
      return

    owned = [b['badge_name'] for b in await db_get_user_badge_instances(payload.user_id)]
    wished = [b['badge_name'] for b in await db_get_simple_wishlist_badges(payload.user_id)]
    # user_locked_badge_names = [b['badge_name'] for b in await db_get_user_badge_instances(payload.user_id, locked=True)]

    if payload.event_type == "REACTION_ADD":
      if badge_name not in owned and badge_name not in wished:
        logger.info(f"Adding {Style.BRIGHT}{badge_name}{Style.RESET_ALL} to {Style.BRIGHT}{member.display_name}'s wishlist{Style.RESET_ALL} via react")
        info = await db_get_badge_info_by_name(badge_name)
        await db_add_badge_info_id_to_wishlist(member.id, info['id'])
        try:
          embed = discord.Embed(
            title="Badge Added to Wishlist",
            description=f"**{badge_name}** has been added to your Wishlist via your ✅ react!",
            color=discord.Color.green()
          )
          embed.set_footer(
            text="Note: You can use /settings to enable or disable these messages."
          )
          await member.send(embed=embed)
        except discord.Forbidden as e:
          logger.info(f"Unable to send wishlist add react confirmation message to {member.display_name}, they have their DMs closed.")
          pass

      elif badge_name in owned:
        logger.info(f"Locking {Style.BRIGHT}{badge_name}{Style.RESET_ALL} in {Style.BRIGHT}{member.display_name}'s inventory{Style.RESET_ALL} via react")
        info = await db_get_badge_info_by_name(badge_name)
        await db_lock_badge_instances_by_badge_info_id(member.id, info['id'])
        if user["receive_notifications"]:
          try:
            embed = discord.Embed(
              title="Badge Locked 🔒",
              description=f"**{badge_name}** has been Locked (across all Tiers) via your ✅ react!\n\nYou can use `/wishlist unlock` if you did this by accident!",
              color=discord.Color.green()
            )
            embed.set_footer(
              text="Note: You can use /settings to enable or disable these messages."
            )
            await member.send(embed=embed)
          except discord.Forbidden as e:
            logger.info(f"Unable to send wishlist add react confirmation message to {member.display_name}, they have their DMs closed.")
            pass
    else:
      if badge_name in wished:
        logger.info(f"Removing {Style.BRIGHT}{badge_name}{Style.RESET_ALL} from {Style.BRIGHT}{member.display_name}'s wishlist{Style.RESET_ALL} via react")
        info = await db_get_badge_info_by_name(badge_name)
        await db_remove_badge_info_id_from_wishlist(member.id, info['id'])
        try:
          embed = discord.Embed(
            title="Badge Removed from Wishlist",
            description=f"**{badge_name}** has been removed from your wishlist via your removal of the ✅ react!",
            color=discord.Color.green()
          )
          embed.set_footer(
            text="Note: You can use /settings to enable or disable these messages."
          )
          await member.send(embed=embed)
        except discord.Forbidden as e:
          logger.info(f"Unable to send wishlist add react confirmation message to {member.display_name}, they have their DMs closed.")
          pass

  # ________  .__               .__
  # \______ \ |__| ____________ |  | _____  ___.__.
  #  |    |  \|  |/  ___/\____ \|  | \__  \<   |  |
  #  |    `   \  |\___ \ |  |_> >  |__/ __ \\___  |
  # /_______  /__/____  >|   __/|____(____  / ____|
  #         \/        \/ |__|             \/\/
  @wishlist_group.command(
    name="display",
    description="List all of the badges on your current unfulfilled wishlist for a given Prestige Tier."
  )
  @option(
    name="prestige",
    description="Which Prestige Tier Wishlist to Display",
    required=True,
    autocomplete=autocomplete_prestige_tiers
  )
  @commands.check(access_check)
  async def display(self, ctx: discord.ApplicationContext, prestige: str):
    await ctx.defer(ephemeral=True)
    user_id = ctx.author.id

    # Validate the selected prestige tier
    if not await is_prestige_valid(ctx, prestige):
      return
    prestige_level = int(prestige)

    logger.info(f"{ctx.author.display_name} is {Style.BRIGHT}displaying their wishlist{Style.RESET_ALL} for the {Style.BRIGHT}{PRESTIGE_TIERS[prestige_level]}{Style.RESET_ALL} Prestige Tier")

    # Fetch badges the user still needs at this prestige level
    wishes = await db_get_active_wants(user_id, prestige_level)

    # No active wants: user has them all
    if not wishes:
      await ctx.followup.send(
        embed=discord.Embed(
          title="No Badges Needed",
          description=f"You've already collected all your desired wishlist badges at the {PRESTIGE_TIERS[prestige_level]} tier!",
          color=discord.Color.green()
        ),
        ephemeral=True
      )
      return

    # Paginate the active wants
    max_per_page = 30
    pages_data = [
      wishes[i : i + max_per_page]
      for i in range(0, len(wishes), max_per_page)
    ]

    pages_list = []
    for idx, page in enumerate(pages_data, start=1):
      embed = discord.Embed(
        title=f"{ctx.author.display_name}'s Wishlist [{PRESTIGE_TIERS[prestige_level]}] Tier",
        description="\n".join(
          f"[{b['badge_name']}]({b['badge_url']})" for b in page
        ),
        color=discord.Color.blurple()
      )
      embed.set_footer(text=f"Page {idx} of {len(pages_data)}")
      pages_list.append(embed)

    paginator = pages.Paginator(
      author_check=False,
      pages=pages_list,
      loop_pages=True,
      disable_on_timeout=True
    )
    await paginator.respond(ctx.interaction, ephemeral=True)


  #    _____          __         .__
  #   /     \ _____ _/  |_  ____ |  |__   ____   ______
  #  /  \ /  \\__  \\   __\/ ___\|  |  \_/ __ \ /  ___/
  # /    Y    \/ __ \|  | \  \___|   Y  \  ___/ \___ \
  # \____|__  (____  /__|  \___  >___|  /\___  >____  >
  #         \/     \/          \/     \/     \/     \/
  @wishlist_group.command(
    name="matches",
    description="Find matches from other users who have what you want, and want what you have!"
  )
  @option(
    name="prestige",
    description="Which Prestige Tier to check",
    required=True,
    autocomplete=autocomplete_prestige_tiers
  )
  @commands.check(access_check)
  async def matches(self, ctx: discord.ApplicationContext, prestige: str):
    await ctx.defer(ephemeral=True)
    user_id = ctx.author.id

    if not await is_prestige_valid(ctx, prestige):
      return
    prestige = int(prestige)

    # Purge any stale dismissals for this tier before fetching matches
    await self._purge_invalid_wishlist_dismissals(user_id, prestige)

    # Fetch active 'wants' at this tier
    wants = await db_get_active_wants(user_id, prestige)
    if not wants:
      await ctx.followup.send(
        embed=discord.Embed(
          title="Wishlist Complete",
          description=f"You have no {PRESTIGE_TIERS[prestige]} Badges missing from your Wishlist!",
          color=discord.Color.red()
        ).set_footer(text="You can add more with `/wishlist add` or `/wishlist add_set`"),
        ephemeral=True
      )
      return

    if await db_has_user_opted_out_of_prestige_matches(user_id, prestige):
      await ctx.followup.send(embed=discord.Embed(
        title="Matchmaking Disabled!",
        description=f"You have opted out of Wishlist matchmaking at the **{PRESTIGE_TIERS[prestige]}** tier.\n\n"
                    "You may re-enable it via `/wishlist opt_out` to see matches again.",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    # Fetch raw matches via SQL CTE
    raw_matches = await db_get_wishlist_matches(user_id, prestige)

    # Remove any partners who have opted out of matchmaking at this tier
    opted_out_partners = set(await db_get_all_prestige_match_opted_out_user_ids(prestige))
    raw_matches = [
      m for m in raw_matches
      if m['match_discord_id'] not in opted_out_partners
    ]

    # Pull out any dismissed partners at this prestige
    all_dismissals = await db_get_all_wishlist_dismissals(user_id)
    dismissed_partners = {
      d['match_discord_id']
      for d in all_dismissals
      if d['prestige_level'] == prestige
    }

    # Filter them out
    matches = [
      m for m in raw_matches
      if m['match_discord_id'] not in dismissed_partners
    ]

    if not matches:
      await ctx.followup.send(
        embed=discord.Embed(
          title=f"No {PRESTIGE_TIERS[prestige]} Matches Found",
          description=(
            f"No users currently have what you want *and* want what you have!"
          ),
          color=discord.Color.blurple()
        ).set_footer(text="Use `/wishlist add` to add more Badges to your overall Wishlist and try to find more matches!"),
        ephemeral=True
      )
      return

    minimum_match_found = False
    # Build paginated page groups for each match
    for m in matches:
      try:
        partner = await bot.current_guild.fetch_member(m['match_discord_id'])
        # parse the new ID arrays
        has_ids   = json.loads(m['badge_ids_you_want_that_they_have'])
        wants_ids = json.loads(m['badge_ids_they_want_that_you_have'])

        max_per_page = 30
        # Paginator for "What You Want"
        has_pages = []
        has_badges_sorted = sorted(json.loads(m['badges_you_want_that_they_have']), key=lambda b: b['name'].casefold())
        has_chunks = [has_badges_sorted[i:i+max_per_page] for i in range(0, len(has_badges_sorted), max_per_page)]
        total_has = len(has_chunks)
        for idx, page_badges in enumerate(has_chunks):
          lines = [f"[{b['name']}]({b['url']})" for b in page_badges]
          embed = discord.Embed(
            title="What You Want",
            description="\n".join(lines) or "No matching badges.",
            color=discord.Color.blurple()
          )
          embed.set_footer(text=f"Match with {partner.display_name}\nPage {idx+1} of {total_has}")
          has_pages.append(embed)

        # Paginator for "What They Want"
        wants_pages = []
        wants_badges_sorted = sorted(json.loads(m['badges_they_want_that_you_have']), key=lambda b: b['name'].casefold())
        wants_chunks = [wants_badges_sorted[i:i+max_per_page] for i in range(0, len(wants_badges_sorted), max_per_page)]
        total_wants = len(wants_chunks)
        for idx, page_badges in enumerate(wants_chunks):
          lines = [f"[{b['name']}]({b['url']})" for b in page_badges]
          embed = discord.Embed(
            title="What They Want",
            description="\n".join(lines) or "No matching badges.",
            color=discord.Color.blurple()
          )
          embed.set_footer(text=f"Match with {partner.display_name}\nPage {idx+1} of {total_wants}")
          wants_pages.append(embed)

        # Dismiss button
        view = discord.ui.View()
        view.add_item(DismissButton(
          self,
          user_id,
          m['match_discord_id'],  # partner
          prestige,
          has_ids,
          wants_ids,
        ))

        # Assemble page groups
        page_groups = [
          pages.PageGroup(
            pages=[
              discord.Embed(
                title=f"Wishlist Match! [{PRESTIGE_TIERS[prestige]}] Tier",
                description=f"{partner.mention} ({partner.display_name}) has a wishlist match with you!",
                color=discord.Color.blurple()
              )
            ],
            label=f"{partner.display_name}'s Match!",
            description="Details and Info",
            custom_buttons=paginator_buttons,
            use_default_buttons=False,
            custom_view=view
          ),
          pages.PageGroup(
            pages=has_pages,
            label="What You Want",
            description="Badges They Have From Your Wishlist",
            custom_buttons=paginator_buttons,
            use_default_buttons=False,
            custom_view=view
          ),
          pages.PageGroup(
            pages=wants_pages,
            label="What They Want",
            description="Badges They Want From Your Inventory",
            custom_buttons=paginator_buttons,
            use_default_buttons=False,
            custom_view=view
          )
        ]

        # Send paginator
        paginator = WishlistPaginator(
          pages=page_groups,
          show_menu=True,
          custom_buttons=paginator_buttons,
          use_default_buttons=False,
          custom_view=view
        )
        await paginator.respond(ctx.interaction, ephemeral=True)
        minimum_match_found = True
      except discord.errors.NotFound as e:
        # Member is no longer on server, clear and ignore
        defunct_member_id = m['match_discord_id']
        await db_clear_wishlist(defunct_member_id)
        pass

    if not minimum_match_found:
      await ctx.followup.send(
        embed=discord.Embed(
          title="No Active Members!",
          description=f"You had one or more matches but the relevant Member(s) are no longer active on the server!\n\nTheir wishlist(s) have been cleared.",
          color=discord.Color.blurple()
        ),
        ephemeral=True
      )
      return

  @wishlist_group.command(
    name="dismissals",
    description="Review any wishlist matches which have been dismissed"
  )
  @option(
    name="prestige",
    description="Which Prestige Tier to check",
    required=True,
    autocomplete=autocomplete_prestige_tiers
  )
  @commands.check(access_check)
  async def dismissals(self, ctx: discord.ApplicationContext, prestige: str):
    await ctx.defer(ephemeral=True)
    user_id = ctx.author.id

    if not await is_prestige_valid(ctx, prestige):
      return
    prestige_level = int(prestige)

    logger.info(
      f"{ctx.author.display_name} is reviewing their dismissals at the "
      f"{PRESTIGE_TIERS[prestige_level]} tier"
    )

    # purge any stale dismissal records for this tier
    await self._purge_invalid_wishlist_dismissals(user_id, prestige_level)

    # fetch all dismissals, then filter to this prestige
    records = await db_get_all_wishlist_dismissals(user_id)
    recs = [r for r in records if r['prestige_level'] == prestige_level]
    if not recs:
      await ctx.followup.send(
        embed=discord.Embed(
          title="No Wishlist Dismissals Found",
          description=(
            f"You have no dismissed matches at the "
            f"{PRESTIGE_TIERS[prestige_level]} Tier."
          ),
          color=discord.Color.blurple()
        ),
        ephemeral=True
      )
      return

    # group by partner
    groups: dict[int, list[dict]] = {}
    for r in recs:
      pid = r['match_discord_id']
      groups.setdefault(pid, []).append(r)

    any_shown = False
    for partner_id, rows in groups.items():
      try:
        partner = await bot.current_guild.fetch_member(partner_id)

        # split out has vs wants
        has_ids = [r['badge_info_id'] for r in rows if r['role'] == 'has']
        wants_ids = [r['badge_info_id'] for r in rows if r['role'] == 'wants']

        # fetch badge info for display
        has_infos = [await db_get_badge_info_by_id(b) for b in has_ids]
        wants_infos = [await db_get_badge_info_by_id(b) for b in wants_ids]

        has_lines = [f"[{b['badge_name']}]({b['badge_url']})" for b in has_infos]
        wants_lines = [f"[{b['badge_name']}]({b['badge_url']})" for b in wants_infos]

        # paginate each list
        max_per_page = 30

        all_has_pages = [
          has_lines[i:i+max_per_page]
          for i in range(0, len(has_lines), max_per_page)
        ]
        has_pages = []
        for idx, chunk in enumerate(all_has_pages, start=1):
          e = discord.Embed(
            title="Has From Your Wishlist:",
            description="\n".join(chunk),
            color=discord.Color.blurple()
          )
          e.set_footer(
            text=f"Match with {partner.display_name}\nPage {idx} of {len(all_has_pages)}"
          )
          has_pages.append(e)

        all_wants_pages = [
          wants_lines[i:i+max_per_page]
          for i in range(0, len(wants_lines), max_per_page)
        ]
        wants_pages = []
        for idx, chunk in enumerate(all_wants_pages, start=1):
          e = discord.Embed(
            title="Wants From Your Inventory:",
            description="\n".join(chunk),
            color=discord.Color.blurple()
          )
          e.set_footer(
            text=f"Match with {partner.display_name}\nPage {idx} of {len(all_wants_pages)}"
          )
          wants_pages.append(e)

        # build revoke button
        view = discord.ui.View()
        view.add_item(RevokeDismissalButton(
          self,
          user_id,
          partner_id,
          prestige_level
        ))

        # assemble paginator
        page_groups = [
          pages.PageGroup(
            pages=[
              discord.Embed(
                title=f"Dismissed Match [{PRESTIGE_TIERS[prestige_level]}] Tier",
                description=(
                  f"{partner.mention} ({partner.display_name}) had a wishlist match with you that has been dismissed."
                ),
                color=discord.Color.blurple()
              )
            ],
            label=f"{partner.display_name}'s Dismissed Match!",
            description="Details and Info",
            custom_buttons=paginator_buttons,
            use_default_buttons=False,
            custom_view=view
          ),
          pages.PageGroup(
            pages=has_pages,
            label="What You Wanted",
            description="Badges They Have From Your Wishlist",
            custom_buttons=paginator_buttons,
            use_default_buttons=False,
            custom_view=view
          ),
          pages.PageGroup(
            pages=wants_pages,
            label="What They Wanted",
            description="Badges They Want From Your Inventory",
            custom_buttons=paginator_buttons,
            use_default_buttons=False,
            custom_view=view
          )
        ]

        paginator = WishlistPaginator(
          pages=page_groups,
          show_menu=True,
          custom_buttons=paginator_buttons,
          use_default_buttons=False,
          custom_view=view
        )
        await paginator.respond(ctx.interaction, ephemeral=True)
        any_shown = True

      except discord.errors.NotFound:
        # partner left: clear their wishlist entirely
        await db_clear_wishlist(partner_id)
        continue

    if not any_shown:
      await ctx.followup.send(
        embed=discord.Embed(
          title="No Active Members!",
          description=(
            "You had one or more dismissals but the relevant Member(s) are no longer active on the server!\n\nTheir wishlist(s) have been cleared."
          ),
          color=discord.Color.blurple()
        ),
        ephemeral=True
      )


  async def _purge_invalid_wishlist_dismissals(self, user_id: str, prestige: int):
    current = await db_get_wishlist_matches(user_id, prestige)
    valid = {}
    for m in current:
      pid = m['match_discord_id']
      has_ids = json.loads(m['badge_ids_you_want_that_they_have'])
      wants_ids = json.loads(m['badge_ids_they_want_that_you_have'])
      valid[pid] = (has_ids, wants_ids)

    inventory = await db_get_wishlist_inventory_matches(user_id, prestige)
    partner_ids = {row['user_discord_id'] for row in inventory}
    for pid in partner_ids:
      valid.setdefault(pid, ([], []))

    stored = await db_get_all_wishlist_dismissals(user_id)
    for rec in stored:
      pid = rec['match_discord_id']
      # collect all rows for this partner+prestige
      rows = [
        r for r in stored
        if r['match_discord_id'] == pid and r['prestige_level'] == prestige
      ]
      saved_has = [r['badge_info_id'] for r in rows if r['role'] == 'has']
      saved_wants = [r['badge_info_id'] for r in rows if r['role'] == 'wants']

      valid_has_ids, valid_wants_ids = set(valid.get(pid, ([], []))[0]), set(valid.get(pid, ([], []))[1])
      dismissed_has_ids, dismissed_wants_ids = set(saved_has), set(saved_wants)

      if not dismissed_has_ids.issubset(valid_has_ids) or not dismissed_wants_ids.issubset(valid_wants_ids):
        await db_delete_wishlist_dismissal(user_id, pid, prestige)


  #    _____       .___  .___
  #   /  _  \    __| _/__| _/
  #  /  /_\  \  / __ |/ __ |
  # /    |    \/ /_/ / /_/ |
  # \____|__  /\____ \____ |
  #         \/      \/    \/
  @wishlist_group.command(
    name="add",
    description="Add badges to your Wishlist."
  )
  @option(
    name="badge",
    description="Badge to add to your Wishlist",
    required=True,
    autocomplete=add_autocomplete
  )
  async def add(self, ctx:discord.ApplicationContext, badge:str):
    await ctx.defer(ephemeral=True)
    user_discord_id = ctx.author.id
    try:
      badge_info_id = int(badge)
    except ValueError:
      await ctx.respond(embed=discord.Embed(
        title="Invalid Badge Selection",
        description="Please select a valid badge from the dropdown.",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    badge_info = await db_get_badge_info_by_id(badge_info_id)
    if not badge_info:
      channel = await bot.current_guild.fetch_channel(get_channel_id("megalomaniacal-computer-storage"))
      await ctx.followup.send(
        embed=discord.Embed(
          title="That Badge Doesn't Exist (Yet?)",
          description=f"We don't have that one in our databanks! If you think this is an error please let us know in {channel.mention}!",
          color=discord.Color.red()
        )
      )
      return

    special_badge_ids = {b['id'] for b in await db_get_special_badge_info()}
    if badge_info_id in special_badge_ids:
      await ctx.respond(embed=discord.Embed(
        title="That's a Special Badge",
        description="Special Badges cannot be added to your wishlist!",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    logger.info(f"{ctx.author.display_name} is attempting to {Style.BRIGHT}add{Style.RESET_ALL} the badge {Style.BRIGHT}{badge_info['badge_name']}{Style.RESET_ALL} to their {Style.BRIGHT}wishlist{Style.RESET_ALL}")

    # Badge exists, so we can retrieve the info now
    badge_name = badge_info['badge_name']

    special_badge_ids = [b['id'] for b in await db_get_special_badge_info()]
    if badge_info_id in special_badge_ids:
      await ctx.followup.send(
        embed=discord.Embed(
          title="Invalid Badge Selection!",
          description=f"Unable to complete your request, **{badge_name}** is a ✨ *special badge* ✨ and cannot be acquired via trading!",
          color=discord.Color.red()
        )
      )
      return

    # We're good to actually retrieve the user's wishlist now
    wishlist_badges = await db_get_simple_wishlist_badges(user_discord_id)

    # Check to make sure the badge is not already present in their wishlist
    if badge_info_id in [b['badge_info_id'] for b in wishlist_badges]:
      await ctx.followup.send(
        embed=discord.Embed(
          title="Badge Already Added!",
          description=f"Unable to complete your request, **{badge_name}** is already present in your Wishlist!",
          color=discord.Color.red()
        ).set_footer(text="Maybe you meant to use `/wishlist remove`?")
      )
      return

    # Otherwise, good to go and add the badge
    await db_add_badge_info_id_to_wishlist(user_discord_id, badge_info_id)
    # Then lock it down across all tiers the user may currently possess it at
    await db_lock_badge_instances_by_badge_info_id(user_discord_id, badge_info_id)
    discord_file, attachment_url = await generate_unowned_badge_preview(user_discord_id, badge_info)

    # Determine existing ownership per prestige tier
    instances = await db_get_user_badge_instances(user_discord_id)
    owned_tiers = sorted({
      inst['prestige_level'] for inst in instances
      if inst['badge_info_id'] == badge_info_id
    })

    embed_description = f"You've successfully added **{badge_name}** to your Wishlist."
    if not owned_tiers:
      embed_description += "\n\nYou do not yet own this badge at any of your current unlocked Prestige Tiers."
      embed_description += " It will be used for matching at your current Tier, as well as future Tiers as you continue to progress!"
    else:
      embed_description += "\n\nGood news! You own this badge at some of your unlocked Prestige Tiers! They have been auto-locked now that you have added them to your wishlist."
      embed_description += "\n\nYour new wishlist entry will continue to be used for matching at any existing Tiers you may not have collected it at yet, and will also match at future Tiers as you unlock them!"

    embed = discord.Embed(
      title="Badge Added Successfully",
      description=embed_description,
      color=discord.Color.green()
    )
    embed.set_footer(text="Check `/wishlist matches` periodically to see if you can find some traders!")
    if owned_tiers:
      echelon_progress = await db_get_echelon_progress(user_discord_id)
      current_prestige_tier = echelon_progress['current_prestige_tier']
      for tier in range(current_prestige_tier + 1):
        owned = tier in owned_tiers
        symbol = "✅" if owned else "❌"
        embed.add_field(
          name=PRESTIGE_TIERS[tier],
          value=f"Owned: {symbol}",
          inline=False
        )

    embed.set_image(url=attachment_url)
    await ctx.followup.send(embed=embed, file=discord_file)


  #    _____       .___  .____________       __
  #   /  _  \    __| _/__| _/   _____/ _____/  |_
  #  /  /_\  \  / __ |/ __ |\_____  \_/ __ \   __\
  # /    |    \/ /_/ / /_/ |/        \  ___/|  |
  # \____|__  /\____ \____ /_______  /\___  >__|
  #         \/      \/    \/       \/     \/
  @wishlist_group.command(
    name="add_set",
    description="Add a full set of badges to your Wishlist."
  )
  @option(
    name="category",
    description="Which category of set?",
    required=True,
    choices=[
      discord.OptionChoice(
        name="Affiliation",
        value="affiliation"
      ),
      discord.OptionChoice(
        name="Franchise",
        value="franchise"
      ),
      discord.OptionChoice(
        name="Time Period",
        value="time_period"
      ),
      discord.OptionChoice(
        name="Type",
        value="type"
      )
    ]
  )
  @option(
    name="selection",
    description="Which one?",
    required=True,
    autocomplete=autocomplete_selections
  )
  async def add_set(self, ctx:discord.ApplicationContext, category:str, selection:str):
    await ctx.defer(ephemeral=True)
    user_discord_id = ctx.author.id

    logger.info(f"{ctx.author.display_name} is attempting to {Style.BRIGHT}add a set{Style.RESET_ALL}, {Style.BRIGHT}{category} - {selection}{Style.RESET_ALL}, to their {Style.BRIGHT}wishlist{Style.RESET_ALL}")

    if category == 'affiliation':
      all_set_badges = await db_get_all_affiliation_badges(selection)
    elif category == 'franchise':
      all_set_badges = await db_get_all_franchise_badges(selection)
    elif category == 'time_period':
      all_set_badges = await db_get_all_time_period_badges(selection)
    elif category == 'type':
      all_set_badges = await db_get_all_type_badges(selection)
    else:
      await ctx.followup.send(
        embed=discord.Embed(
          title="Invalid Category",
          description=f"The category `{category}` does not match our databanks, please select a valid category from the list!",
          color=discord.Color.red()
        )
      )
      return

    category_title = category.replace("_", " ").title()

    if not all_set_badges:
      await ctx.followup.send(
        embed=discord.Embed(
          title=f"Your entry was not in the list of {category_title}s!",
          color=discord.Color.red()
        )
      )
      return

    wishlist_badges = await db_get_simple_wishlist_badges(user_discord_id)
    wishlist_badge_ids = {b['badge_info_id'] for b in wishlist_badges}
    all_set_badge_ids = {b['id'] for b in all_set_badges}

    # Exclude special badges from being added at all
    special_badge_ids = {b['id'] for b in await db_get_special_badge_info()}
    all_set_badge_ids -= special_badge_ids

    valid_badge_info_ids = [id for id in all_set_badge_ids if id not in wishlist_badge_ids]
    existing_badge_info_ids = [id for id in all_set_badge_ids if id in wishlist_badge_ids]

    # Otherwise go ahead and add them
    await db_add_badge_info_ids_to_wishlist(user_discord_id, valid_badge_info_ids)
    # Auto-lock the new ones
    await db_lock_badge_instances_by_badge_info_ids(user_discord_id, valid_badge_info_ids)
    # Auto-lock existing ones
    await db_lock_badge_instances_by_badge_info_ids(user_discord_id, existing_badge_info_ids)

    embed = discord.Embed(
      title="Badge Set Added Successfully",
      description=f"You've successfully added all of the `{selection}` Badges to your Wishlist that you do not currently possess.\n\n"
                   "They will be used for matching at your current Tier, as well as future Tiers as you continue to progress! "
                   "Any Badges you may already possess from this set have been Locked across all Prestige Tiers.",
      color=discord.Color.green()
    )
    await ctx.followup.send(embed=embed)


  # __________
  # \______   \ ____   _____   _______  __ ____
  #  |       _// __ \ /     \ /  _ \  \/ // __ \
  #  |    |   \  ___/|  Y Y  (  <_> )   /\  ___/
  #  |____|_  /\___  >__|_|  /\____/ \_/  \___  >
  #         \/     \/      \/                 \/
  @wishlist_group.command(
    name="remove",
    description="Remove a badge from your wishlist."
  )
  @option(
    name="badge",
    description="Badge to remove",
    required=True,
    autocomplete=remove_autocomplete
  )
  async def remove(self, ctx:discord.ApplicationContext, badge:str):
    await ctx.defer(ephemeral=True)
    user_discord_id = ctx.author.id
    try:
      badge_info_id = int(badge)
    except ValueError:
      await ctx.respond(embed=discord.Embed(
        title="Invalid Badge Selection",
        description="Please select a valid badge from the dropdown.",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    badge_info = await db_get_badge_info_by_id(badge_info_id)
    badge_name = badge_info['badge_name']

    logger.info(f"{ctx.author.display_name} is attempting to {Style.BRIGHT}remove {Style.RESET_ALL} the badge {Style.BRIGHT}{badge_name} {Style.RESET_ALL} from their {Style.BRIGHT}wishlist{Style.RESET_ALL}")

    # Check to make sure the badges are present in their wishlist
    if not await db_is_badge_on_users_wishlist(user_discord_id, badge_info_id):
      await ctx.followup.send(embed=discord.Embed(
        title="Badge Not Present in Wishlist!",
        description=f"Unable to complete your request, `{badge_name}` is not present in your Wishlist",
        color=discord.Color.red()
      ))
      return

    # If they are go ahead and remove the badges
    await db_remove_badge_info_id_from_wishlist(user_discord_id, badge_info_id)

    await ctx.followup.send(embed=discord.Embed(
      title="Badge Removed Successfully",
      description=f"You've successfully removed `{badge_name}` from your wishlist",
      color=discord.Color.green()
    ))


  # __________                                    _________       __
  # \______   \ ____   _____   _______  __ ____  /   _____/ _____/  |_
  #  |       _// __ \ /     \ /  _ \  \/ // __ \ \_____  \_/ __ \   __\
  #  |    |   \  ___/|  Y Y  (  <_> )   /\  ___/ /        \  ___/|  |
  #  |____|_  /\___  >__|_|  /\____/ \_/  \___  >_______  /\___  >__|
  #         \/     \/      \/                 \/        \/     \/
  @wishlist_group.command(
    name="remove_set",
    description="Remove a full set of badges from your Wishlist."
  )
  @option(
    name="category",
    description="Which category of set?",
    required=True,
    choices=[
      discord.OptionChoice(name="Affiliation", value="affiliation"),
      discord.OptionChoice(name="Franchise", value="franchise"),
      discord.OptionChoice(name="Time Period", value="time_period"),
      discord.OptionChoice(name="Type", value="type")
    ]
  )
  @option(
    name="selection",
    description="Which one?",
    required=True,
    autocomplete=autocomplete_selections
  )
  async def remove_set(self, ctx:discord.ApplicationContext, category:str, selection:str):
    await ctx.defer(ephemeral=True)
    user_discord_id = ctx.author.id

    logger.info(f"{ctx.author.display_name} is attempting to {Style.BRIGHT}remove a set{Style.RESET_ALL}, {Style.BRIGHT}{category} - {selection}{Style.RESET_ALL}, from their {Style.BRIGHT}wishlist{Style.RESET_ALL}")

    if category == 'affiliation':
      all_set_badges = await db_get_all_affiliation_badges(selection)
    elif category == 'franchise':
      all_set_badges = await db_get_all_franchise_badges(selection)
    elif category == 'time_period':
      all_set_badges = await db_get_all_time_period_badges(selection)
    elif category == 'type':
      all_set_badges = await db_get_all_type_badges(selection)
    else:
      await ctx.followup.send(
        embed=discord.Embed(
          title="Invalid Category",
          description=f"The category `{category}` does not match our databanks, please select a valid category from the list!",
          color=discord.Color.red()
        )
      )
      return

    category_title = category.replace("_", " ").title()

    if not all_set_badges:
      await ctx.followup.send(
        embed=discord.Embed(
          title=f"Your entry was not in the list of {category_title}s!",
          color=discord.Color.red()
        )
      )
      return

    wishlist_badges = await db_get_simple_wishlist_badges(user_discord_id)
    wishlist_badge_ids = {b['badge_info_id'] for b in wishlist_badges}
    all_set_badge_ids = {b['id'] for b in all_set_badges}
    valid_badge_info_ids = [id for id in all_set_badge_ids if id in wishlist_badge_ids]

    # Filter out special badges before unlocking
    special_badge_ids = {b['id'] for b in await db_get_special_badge_info()}
    safe_to_unlock_ids = [id for id in valid_badge_info_ids if id not in special_badge_ids]

    # Go ahead and remove from wishlist
    await db_remove_badge_info_ids_from_wishlist(user_discord_id, [id for id in valid_badge_info_ids if id not in special_badge_ids])

    embed = discord.Embed(
      title="Badge Set Removed Successfully",
      description=f"You've successfully removed all of the `{selection}` Badges from your Wishlist.\n\n"
                   "They will no longer used for matching at your current Prestige Tier, as well as future Tiers as you continue to progress.",
      color=discord.Color.green()
    )
    await ctx.followup.send(embed=embed)


  @wishlist_group.command(
    name="clear",
    description="Remove all badges from your Wishlist."
  )
  @option(
    name="confirm",
    description="Confirm you wish to clear your Wishlist",
    required=True,
    choices=[
      discord.OptionChoice(
        name="No, don't clear.",
        value="no"
      ),
      discord.OptionChoice(
        name="Yes, clear my Wishlist.",
        value="yes"
      )
    ]
  )
  async def clear(self, ctx:discord.ApplicationContext, confirm:str):
    await ctx.defer(ephemeral=True)
    confirmed = bool(confirm == "yes")

    user_discord_id = ctx.author.id

    logger.info(f"{ctx.author.display_name} is attempting to {Style.BRIGHT}clear{Style.RESET_ALL} their {Style.BRIGHT}wishlist{Style.RESET_ALL}")

    if confirmed:
      await db_clear_wishlist(user_discord_id)
      logger.info(f"{ctx.author.display_name} has {Style.BRIGHT}cleared {Style.RESET_ALL} their {Style.BRIGHT}wishlist{Style.RESET_ALL}")

      embed = discord.Embed(
        title="Wishlist Cleared Successfully",
        description=f"You've successfully removed all badges from your Wishlist.",
        color=discord.Color.green()
      )
      await ctx.followup.send(embed=embed)
    else:
      embed = discord.Embed(
        title="No Action Taken",
        description=f"Confirmation was not verified. If you intend to clear your wishlist, please select Yes as your confirmation choice.",
        color=discord.Color.red()
      )
      await ctx.followup.send(embed=embed)


  # .____                  __
  # |    |    ____   ____ |  | __
  # |    |   /  _ \_/ ___\|  |/ /
  # |    |__(  <_> )  \___|    <
  # |_______ \____/ \___  >__|_ \
  #         \/          \/     \/
  @wishlist_group.command(
    name="lock",
    description="Lock a badge from being listed in Wishlist matches."
  )
  @option(
    name="badge",
    description="Badge to Lock",
    required=True,
    autocomplete=lock_autocomplete
  )
  async def lock(self, ctx: discord.ApplicationContext, badge: str):
    await ctx.defer(ephemeral=True)
    user_discord_id = ctx.author.id

    try:
      badge_info_id = int(badge)
    except ValueError:
      await ctx.respond(embed=discord.Embed(
        title="Invalid Badge Selection",
        description="Please select a valid badge from the dropdown.",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    logger.info(f"{ctx.author.display_name} is attempting to {Style.BRIGHT}lock{Style.RESET_ALL} the badge {Style.BRIGHT}{badge}{Style.RESET_ALL} from being listed in their {Style.BRIGHT}wishlist{Style.RESET_ALL}")

    badge_info = await db_get_badge_info_by_id(badge_info_id)
    if not badge_info:
      channel = await bot.current_guild.fetch_channel(get_channel_id("megalomaniacal-computer-storage"))
      await ctx.followup.send(embed=discord.Embed(
        title="That Badge Doesn't Exist (Yet?)",
        description=f"We don't have that one in our databanks! If you think this is an error please let us know in {channel.mention}!",
        color=discord.Color.red()
      ))
      return

    badge_name = badge_info['badge_name']

    # Perform the lock
    await db_lock_badge_instances_by_badge_info_id(user_discord_id, badge_info_id)

    # Re-fetch instance state
    all_instances = await db_get_user_badge_instances(user_discord_id, prestige=None)

    owned_tiers = {
      i['prestige_level']
      for i in all_instances
      if i['badge_info_id'] == badge_info_id and i['active']
    }
    locked_tiers = {
      i['prestige_level']
      for i in all_instances
      if i['badge_info_id'] == badge_info_id and i['active'] and i['locked']
    }

    discord_file, attachment_url = await generate_unowned_badge_preview(user_discord_id, badge_info)

    embed = discord.Embed(
      title="Badge Locked Successfully",
      description=f"You've successfully locked `{badge_name}` from being listed in Wishlist matches (in the Prestige Tiers at which you possess it)!",
      color=discord.Color.green()
    )
    embed.set_image(url=attachment_url)

    echelon_progress = await db_get_echelon_progress(user_discord_id)
    current_prestige_tier = echelon_progress['current_prestige_tier']

    for tier in range(current_prestige_tier + 1):
      if tier in owned_tiers:
        if tier in locked_tiers:
          symbol = "🔒"
          note = " (Locked)"
        else:
          symbol = "✅"
          note = " (Unlocked)"
      else:
        symbol = "❌"
        note = ""
      embed.add_field(
        name=PRESTIGE_TIERS[tier],
        value=f"Owned: {symbol}{note}",
        inline=False
      )

    await ctx.followup.send(embed=embed, file=discord_file)



  # .____                  __      _________       __
  # |    |    ____   ____ |  | __ /   _____/ _____/  |_
  # |    |   /  _ \_/ ___\|  |/ / \_____  \_/ __ \   __\
  # |    |__(  <_> )  \___|    <  /        \  ___/|  |
  # |_______ \____/ \___  >__|_ \/_______  /\___  >__|
  #         \/          \/     \/        \/     \/
  @wishlist_group.command(
    name="lock_set",
    description="Lock your current items in a set from being listed in Wishlist matches."
  )
  @option(
    name="category",
    description="Which category of set?",
    required=True,
    choices=[
      discord.OptionChoice(
        name="Affiliation",
        value="affiliation"
      ),
      discord.OptionChoice(
        name="Franchise",
        value="franchise"
      ),
      discord.OptionChoice(
        name="Time Period",
        value="time_period"
      ),
      discord.OptionChoice(
        name="Type",
        value="type"
      )
    ]
  )
  @option(
    name="selection",
    description="Which one?",
    required=True,
    autocomplete=autocomplete_selections
  )
  async def lock_set(self, ctx:discord.ApplicationContext, category:str, selection:str):
    await ctx.defer(ephemeral=True)
    user_discord_id = ctx.author.id

    logger.info(f"{ctx.author.display_name} is attempting to {Style.BRIGHT}lock a set{Style.RESET_ALL}, {Style.BRIGHT}{category} - {selection}{Style.RESET_ALL}, from being listed in their {Style.BRIGHT}wishlist{Style.RESET_ALL}")

    if category == 'affiliation':
      all_set_badges = await db_get_all_affiliation_badges(selection)
    elif category == 'franchise':
      all_set_badges = await db_get_all_franchise_badges(selection)
    elif category == 'time_period':
      all_set_badges = await db_get_all_time_period_badges(selection)
    elif category == 'type':
      all_set_badges = await db_get_all_type_badges(selection)
    else:
      await ctx.followup.send(
        embed=discord.Embed(
          title="Invalid Category",
          description=f"The category `{category}` does not match our databanks, please select a valid category from the list!",
          color=discord.Color.red()
        )
      )
      return

    category_title = category.replace("_", " ").title()

    if not all_set_badges:
      await ctx.followup.send(
        embed=discord.Embed(
          title=f"Your entry was not in the list of {category_title}s!",
          color=discord.Color.red()
        )
      )
      return

    all_set_badge_ids = [b['id'] for b in all_set_badges]
    await db_lock_badge_instances_by_badge_info_ids(user_discord_id, all_set_badge_ids)

    embed = discord.Embed(
      title="Badge Set Locked Successfully",
      description=f"You've successfully locked all of the `{selection}` badges in your inventory from being listed in Wishlist matches (in the Prestige Tiers at which you possess it)!",
      color=discord.Color.green()
    )
    await ctx.followup.send(embed=embed)

  #  ____ ___      .__                 __
  # |    |   \____ |  |   ____   ____ |  | __
  # |    |   /    \|  |  /  _ \_/ ___\|  |/ /
  # |    |  /   |  \  |_(  <_> )  \___|    <
  # |______/|___|  /____/\____/ \___  >__|_ \
  #              \/                 \/     \/
  @wishlist_group.command(
    name="unlock",
    description="Unlock a badge so that it is listed again in Wishlist matches."
  )
  @option(
    name="badge",
    description="Badge to unlock",
    required=True,
    autocomplete=unlock_autocomplete
  )
  async def unlock(self, ctx: discord.ApplicationContext, badge: str):
    await ctx.defer(ephemeral=True)
    user_discord_id = ctx.author.id

    try:
      badge_info_id = int(badge)
    except ValueError:
      await ctx.respond(embed=discord.Embed(
        title="Invalid Badge Selection",
        description="Please select a valid badge from the dropdown.",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    logger.info(f"{ctx.author.display_name} is attempting to {Style.BRIGHT}unlock {Style.RESET_ALL} the badge {Style.BRIGHT}{badge}{Style.RESET_ALL} from being listed in their {Style.BRIGHT}wishlist{Style.RESET_ALL}")

    badge_info = await db_get_badge_info_by_id(badge_info_id)
    if not badge_info:
      channel = await bot.current_guild.fetch_channel(get_channel_id("megalomaniacal-computer-storage"))
      await ctx.followup.send(embed=discord.Embed(
        title="That Badge Doesn't Exist (Yet?)",
        description=f"We don't have that one in our databanks! If you think this is an error please let us know in {channel.mention}!",
        color=discord.Color.red()
      ))
      return

    badge_name = badge_info['badge_name']

    # Perform the unlock
    await db_unlock_badge_instances_by_badge_info_id(user_discord_id, badge_info_id)

    # Re-fetch instance state
    all_instances = await db_get_user_badge_instances(user_discord_id, prestige=None)

    owned_tiers = {
      i['prestige_level']
      for i in all_instances
      if i['badge_info_id'] == badge_info_id and i['active']
    }
    locked_tiers = {
      i['prestige_level']
      for i in all_instances
      if i['badge_info_id'] == badge_info_id and i['active'] and i['locked']
    }

    discord_file, attachment_url = await generate_unowned_badge_preview(user_discord_id, badge_info)

    embed = discord.Embed(
      title="Badge Unlocked Successfully",
      description=f"You've successfully unlocked `{badge_name}` for Wishlist matching (in the Prestige Tiers at which you possess it)!",
      color=discord.Color.green()
    )
    embed.set_image(url=attachment_url)

    echelon_progress = await db_get_echelon_progress(user_discord_id)
    current_prestige_tier = echelon_progress['current_prestige_tier']

    for tier in range(current_prestige_tier + 1):
      if tier in owned_tiers:
        if tier in locked_tiers:
          symbol = "🔒"
          note = " (Locked)"
        else:
          symbol = "✅"
          note = " (Unlocked)"
      else:
        symbol = "❌"
        note = ""
      embed.add_field(
        name=PRESTIGE_TIERS[tier],
        value=f"Owned: {symbol}{note}",
        inline=False
      )

    await ctx.followup.send(embed=embed, file=discord_file)


  #  ____ ___                     __      _________       __
  # |    |   \____   ____   ____ |  | __ /   _____/ _____/  |_
  # |    |   /    \ /  _ \_/ ___\|  |/ / \_____  \_/ __ \   __\
  # |    |  /   |  (  <_> )  \___|    <  /        \  ___/|  |
  # |______/|___|  /\____/ \___  >__|_ \/_______  /\___  >__|
  #              \/            \/     \/        \/     \/
  @wishlist_group.command(
    name="unlock_set",
    description="Unlock your current items in a set so they are listed in Wishlist matches."
  )
  @option(
    name="category",
    description="Which category of set?",
    required=True,
    choices=[
      discord.OptionChoice(
        name="Affiliation",
        value="affiliation"
      ),
      discord.OptionChoice(
        name="Franchise",
        value="franchise"
      ),
      discord.OptionChoice(
        name="Time Period",
        value="time_period"
      ),
      discord.OptionChoice(
        name="Type",
        value="type"
      )
    ]
  )
  @option(
    name="selection",
    description="Which one?",
    required=True,
    autocomplete=autocomplete_selections
  )
  async def unlock_set(self, ctx:discord.ApplicationContext, category:str, selection:str):
    await ctx.defer(ephemeral=True)
    user_discord_id = ctx.author.id

    logger.info(f"{ctx.author.display_name} is attempting to {Style.BRIGHT}unlock a set{Style.RESET_ALL}, {Style.BRIGHT}{category} - {selection}{Style.RESET_ALL}, from being listed in their {Style.BRIGHT}wishlist{Style.RESET_ALL}")

    if category == 'affiliation':
      all_set_badges = await db_get_all_affiliation_badges(selection)
    elif category == 'franchise':
      all_set_badges = await db_get_all_franchise_badges(selection)
    elif category == 'time_period':
      all_set_badges = await db_get_all_time_period_badges(selection)
    elif category == 'type':
      all_set_badges = await db_get_all_type_badges(selection)
    else:
      await ctx.followup.send(
        embed=discord.Embed(
          title="Invalid Category",
          description=f"The category `{category}` does not match our databanks, please select a valid category from the list!",
          color=discord.Color.red()
        )
      )
      return

    category_title = category.replace("_", " ").title()

    if not all_set_badges:
      await ctx.followup.send(
        embed=discord.Embed(
          title=f"Your entry was not in the list of {category_title}s!",
          color=discord.Color.red()
        )
      )
      return

    all_set_badge_ids = [b['id'] for b in all_set_badges]
    await db_unlock_badge_instances_by_badge_info_ids(user_discord_id, all_set_badge_ids)

    embed = discord.Embed(
      title="Badge Set Unlocked Successfully",
      description=f"You've successfully unlocked all of the `{selection}` badges in your inventory from being listed in Wishlist matches (in the Prestige Tiers at which you possess it)!",
      color=discord.Color.green()
    )
    await ctx.followup.send(embed=embed)

  @wishlist_group.command(
    name="opt_out",
    description="Opt in or out of Wishlist matching at a specific Prestige Tier"
  )
  @option(
    name="prestige",
    description="Which Prestige Tier?",
    required=True,
    autocomplete=autocomplete_prestige_tiers
  )
  @option(
    name="opt_out",
    description="Do you want to opt out of matching at this tier?",
    required=True,
    choices=[
      discord.OptionChoice(name="Yes, opt me out", value="yes"),
      discord.OptionChoice(name="No, opt me back in", value="no")
    ]
  )
  @commands.check(access_check)
  async def opt_out(self, ctx: discord.ApplicationContext, prestige: str, opt_out: str):
    await ctx.defer(ephemeral=True)
    user_id = ctx.author.id

    if not await is_prestige_valid(ctx, prestige):
      return
    prestige_level = int(prestige)
    tier_name = PRESTIGE_TIERS[prestige_level]
    is_opt_out = opt_out.lower() == "yes"
    already_opted_out = await db_has_user_opted_out_of_prestige_matches(user_id, prestige_level)

    # Prevent redundant toggle
    if is_opt_out and already_opted_out:
      await ctx.followup.send(embed=discord.Embed(
        title=f"Already Opted-Out at **{tier_name}**",
        description=f"You're already opted *out* of Wishlist matchmaking at **{tier_name}**.",
        color=discord.Color.orange()
      ), ephemeral=True)
      return
    elif not is_opt_out and not already_opted_out:
      await ctx.followup.send(embed=discord.Embed(
        title=f"Already Opted-In at **{tier_name}**",
        description=f"You're already opted *in* to Wishlist matchmaking at **{tier_name}**.",
        color=discord.Color.orange()
      ), ephemeral=True)
      return

    # Perform toggle
    if is_opt_out:
      await db_add_prestige_opt_out(user_id, prestige_level)
      logger.info(f"{ctx.author.display_name} opted OUT of wishlist matching at {tier_name}")
      embed = discord.Embed(
        title=f"You have disabled Matchmaking at **{tier_name}**",
        description=f"You've opted *out* of Wishlist matchmaking at **{tier_name}**.\n\n"
                    "You will no longer appear in matches at this tier, and won't see others who could match with you.",
        color=discord.Color.red()
      )
    else:
      await db_remove_prestige_opt_out(user_id, prestige_level)
      logger.info(f"{ctx.author.display_name} opted IN to wishlist matching at {tier_name}")
      embed = discord.Embed(
        title=f"You have opted *into* Matchmaking at **{tier_name}**",
        description=f"You've opted back **in** to Wishlist matchmaking at the {tier_name} tier.\n\n"
                    "You may now appear in matches and see others at this tier.",
        color=discord.Color.green()
      )

    # Footer: current opt-outs
    opted_out = await db_get_opted_out_prestiges(user_id)
    if opted_out:
      names = [PRESTIGE_TIERS[t] for t in sorted(opted_out)]
      embed.set_footer(text=f"Currently opted out of: {', '.join(names)}")
    else:
      embed.set_footer(text="You are currently opted-in to all Prestige Tiers.")

    await ctx.followup.send(embed=embed)