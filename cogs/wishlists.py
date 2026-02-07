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
  instances = await db_get_user_badge_instances(user_id, prestige=None)

  # Use badge_filename to dedupe multiple prestige instances
  seen_filenames = set()
  badge_ids = []
  for inst in instances:
    if inst['badge_filename'] not in seen_filenames:
      seen_filenames.add(inst['badge_filename'])
      badge_ids.append(inst['badge_info_id'])

  all_info = await db_get_all_badge_info()
  info_map = {b['id']: b for b in all_info}

  choices = [
    discord.OptionChoice(
      name=info_map[bid]['badge_name'],
      value=str(bid)
    )
    for bid in badge_ids
    if bid in info_map and strip_bullshit(ctx.value.lower()) in strip_bullshit(info_map[bid]['badge_name'].lower())
  ]
  return choices

async def unlock_autocomplete(ctx: discord.AutocompleteContext):
  user_id = ctx.interaction.user.id
  instances = await db_get_user_badge_instances(user_id, locked=True, prestige=None)

  seen_filenames = set()
  badge_ids = []
  for inst in instances:
    if inst['badge_filename'] not in seen_filenames:
      seen_filenames.add(inst['badge_filename'])
      badge_ids.append(inst['badge_info_id'])

  all_info = await db_get_all_badge_info()
  info_map = {b['id']: b for b in all_info}

  choices = [
    discord.OptionChoice(
      name=info_map[bid]['badge_name'],
      value=str(bid)
    )
    for bid in badge_ids
    if bid in info_map and strip_bullshit(ctx.value.lower()) in strip_bullshit(info_map[bid]['badge_name'].lower())
  ]
  return choices


def _wishlist_safe_json_load(value):
  if value is None:
    return []

  if isinstance(value, (list, dict)):
    return value

  if isinstance(value, (bytes, bytearray)):
    try:
      value = value.decode("utf-8", errors="ignore")
    except Exception:
      return []

  if isinstance(value, str):
    value = value.strip()
    if not value:
      return []
    try:
      return json.loads(value)
    except Exception:
      return []

  return []


def _wishlist_build_dismissal_index(
  dismissals: list[dict],
  *,
  prestige_level: int
) -> dict[str, dict[str, set[int]]]:
  """
  Returns:
    {
      "partner_id": {
        "has": {badge_info_id, ...},
        "wants": {badge_info_id, ...}
      }
    }

  role meanings (your table):
    - "wants": dismiss items from "badges_you_want_that_they_have" (you want, they have)
    - "has": dismiss items from "badges_they_want_that_you_have" (they want, you have)
  """
  index: dict[str, dict[str, set[int]]] = {}

  for row in dismissals:
    try:
      if int(row.get("prestige_level", -1)) != int(prestige_level):
        continue
    except Exception:
      continue

    partner_id = row.get("match_discord_id")
    role = row.get("role")
    badge_info_id = row.get("badge_info_id")

    if not partner_id or role not in ("has", "wants"):
      continue

    try:
      badge_info_id = int(badge_info_id)
    except Exception:
      continue

    if partner_id not in index:
      index[partner_id] = {
        "has": set(),
        "wants": set()
      }

    index[partner_id][role].add(badge_info_id)

  return index


async def _wishlist_resolve_member(
  *,
  bot: discord.Bot,
  partner_id: str
) -> discord.Member | None:
  guild = bot.current_guild
  if not guild:
    return None

  try:
    member = guild.get_member(int(partner_id))
  except Exception:
    member = None

  if member:
    return member

  try:
    return await guild.fetch_member(int(partner_id))
  except Exception:
    return None


async def _wishlist_build_matches_partner_dataset(
  *,
  bot: discord.Bot,
  user_id: str,
  prestige_level: int,
  matches: list[dict]
) -> list[dict]:
  """
  Builds partner datasets from db_get_wishlist_matches() rows.

  Applies dismissals per-badge (not per-partner) using db_get_all_wishlist_dismissals().
  Keeps the existing WishlistPartnerView contract:
    - has_lines / wants_lines
    - has_ids / wants_ids
  """
  all_dismissals = await db_get_all_wishlist_dismissals(user_id)
  dismissal_index = _wishlist_build_dismissal_index(all_dismissals, prestige_level=prestige_level)

  partners: list[dict] = []

  for m in matches:
    partner_id = str(m.get("match_discord_id") or "")
    if not partner_id:
      continue

    member = await _wishlist_resolve_member(bot=bot, partner_id=partner_id)
    if not member:
      # Preserve your old behavior:
      # if they are no longer on server, clear their wishlist and skip.
      await db_clear_wishlist(partner_id)
      continue

    # Parse ids arrays
    has_ids = _wishlist_safe_json_load(m.get("badge_ids_you_want_that_they_have"))
    wants_ids = _wishlist_safe_json_load(m.get("badge_ids_they_want_that_you_have"))

    if not isinstance(has_ids, list):
      has_ids = []
    if not isinstance(wants_ids, list):
      wants_ids = []

    has_ids = [int(v) for v in has_ids if str(v).isdigit()]
    wants_ids = [int(v) for v in wants_ids if str(v).isdigit()]

    if not isinstance(has_ids, list):
      has_ids = []
    if not isinstance(wants_ids, list):
      wants_ids = []

    # Normalize to ints
    norm_has_ids: list[int] = []
    for v in has_ids:
      try:
        norm_has_ids.append(int(v))
      except Exception:
        pass

    norm_wants_ids: list[int] = []
    for v in wants_ids:
      try:
        norm_wants_ids.append(int(v))
      except Exception:
        pass

    # Parse badge objects (now includes id/name/url because of the SQL patch)
    has_badges = _wishlist_safe_json_load(m.get("badges_you_want_that_they_have"))
    wants_badges = _wishlist_safe_json_load(m.get("badges_they_want_that_you_have"))

    if not isinstance(has_badges, list):
      has_badges = []
    if not isinstance(wants_badges, list):
      wants_badges = []

    # Apply dismissals per badge id
    dismissed = dismissal_index.get(partner_id, {"has": set(), "wants": set()})
    dismissed_has = dismissed.get("has", set())
    dismissed_wants = dismissed.get("wants", set())

    # Filter ids
    norm_has_ids = [bid for bid in norm_has_ids if bid not in dismissed_wants]
    norm_wants_ids = [bid for bid in norm_wants_ids if bid not in dismissed_has]

    keep_has = set(norm_has_ids)
    keep_wants = set(norm_wants_ids)

    # Filter badge objects by id (requires the SQL patch that adds "id")
    filtered_has_badges = []
    for b in has_badges:
      if not isinstance(b, dict):
        continue
      try:
        bid = int(b.get("id"))
      except Exception:
        continue
      if bid in keep_has:
        filtered_has_badges.append(b)

    filtered_wants_badges = []
    for b in wants_badges:
      if not isinstance(b, dict):
        continue
      try:
        bid = int(b.get("id"))
      except Exception:
        continue
      if bid in keep_wants:
        filtered_wants_badges.append(b)

    # Sort by name
    filtered_has_badges.sort(key=lambda b: str(b.get("name") or "").casefold())
    filtered_wants_badges.sort(key=lambda b: str(b.get("name") or "").casefold())

    has_lines = [
      f"[{b.get('name')}]({b.get('url')})"
      for b in filtered_has_badges
      if b.get("name") and b.get("url")
    ]
    wants_lines = [
      f"[{b.get('name')}]({b.get('url')})"
      for b in filtered_wants_badges
      if b.get("name") and b.get("url")
    ]

    # Drop partners that end up empty after dismissal filtering
    if not has_lines and not wants_lines:
      continue

    partners.append({
      "partner_id": partner_id,
      "partner_name": member.display_name,
      "partner_mention": member.mention,
      "has_lines": has_lines,
      "wants_lines": wants_lines,
      "has_ids": norm_has_ids,
      "wants_ids": norm_wants_ids
    })

  partners.sort(key=lambda p: str(p.get("partner_name") or "").casefold())
  return partners


async def _wishlist_build_dismissals_partner_dataset(
  *,
  bot: discord.Bot,
  groups: dict[str, list[dict]]
) -> list[dict]:
  """
  Builds partner datasets from dismissal rows.

  Keeps the existing WishlistPartnerView contract and uses a local badge_info cache
  to avoid repeated DB calls.
  """
  badge_cache: dict[int, dict] = {}
  partners: list[dict] = []

  async def _get_badge_info_cached(badge_info_id: int) -> dict | None:
    if badge_info_id in badge_cache:
      return badge_cache[badge_info_id]
    info = await db_get_badge_info_by_id(badge_info_id)
    if info:
      badge_cache[badge_info_id] = info
    return info

  for partner_id, rows in groups.items():
    partner_id = str(partner_id)

    member = await _wishlist_resolve_member(bot=bot, partner_id=partner_id)
    if not member:
      await db_clear_wishlist(partner_id)
      continue

    has_ids = []
    wants_ids = []

    for r in rows:
      try:
        bid = int(r.get("badge_info_id"))
      except Exception:
        continue

      if r.get("role") == "has":
        has_ids.append(bid)
      elif r.get("role") == "wants":
        wants_ids.append(bid)

    # Dedup while preserving
    has_ids = list(dict.fromkeys(has_ids))
    wants_ids = list(dict.fromkeys(wants_ids))

    has_infos = []
    for bid in has_ids:
      info = await _get_badge_info_cached(bid)
      if info:
        has_infos.append(info)

    wants_infos = []
    for bid in wants_ids:
      info = await _get_badge_info_cached(bid)
      if info:
        wants_infos.append(info)

    has_infos.sort(key=lambda b: str(b.get("badge_name") or "").casefold())
    wants_infos.sort(key=lambda b: str(b.get("badge_name") or "").casefold())

    has_lines = [
      f"[{b.get('badge_name')}]({b.get('badge_url')})"
      for b in has_infos
      if b.get("badge_name") and b.get("badge_url")
    ]
    wants_lines = [
      f"[{b.get('badge_name')}]({b.get('badge_url')})"
      for b in wants_infos
      if b.get("badge_name") and b.get("badge_url")
    ]

    if not has_lines and not wants_lines:
      continue

    partners.append({
      "partner_id": partner_id,
      "partner_name": member.display_name,
      "partner_mention": member.mention,
      "has_lines": has_lines,
      "wants_lines": wants_lines,
      "has_ids": has_ids,
      "wants_ids": wants_ids
    })

  partners.sort(key=lambda p: str(p.get("partner_name") or "").casefold())
  return partners

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

    info = await db_get_badge_info_by_name(badge_name)
    wished = [b['badge_name'] for b in await db_get_simple_wishlist_badges(payload.user_id)]

    if payload.event_type == "REACTION_ADD":
      logger.info(f"{Style.BRIGHT}{member.display_name}{Style.RESET_ALL} reacted with ✅ to {Style.BRIGHT}{badge_name}{Style.RESET_ALL}")

      # Add to wishlist if not already there
      if badge_name not in wished:
        logger.info(f"Adding {Style.BRIGHT}{badge_name}{Style.RESET_ALL} to wishlist via react")
        await db_add_badge_info_id_to_wishlist(member.id, info['id'])

      # Always lock the badge (all owned tiers)
      logger.info(f"Locking {Style.BRIGHT}{badge_name}{Style.RESET_ALL} via react")
      await db_lock_badge_instances_by_badge_info_id(member.id, info['id'])

      if user['receive_notifications']:
        try:
          # Fresh status
          instances = await db_get_user_badge_instances(payload.user_id, prestige=None)
          owned_tiers = {i['prestige_level'] for i in instances if i['badge_info_id'] == info['id'] and i['active']}
          locked_tiers = {i['prestige_level'] for i in instances if i['badge_info_id'] == info['id'] and i['active'] and i['locked']}
          echelon_progress = await db_get_echelon_progress(payload.user_id)
          current_max_tier = echelon_progress['current_prestige_tier']

          embed = discord.Embed(
            title="Wishlist + Lock Applied",
            description=f"**{badge_name}** has been Added to your Wishlist and Locked (at owned Tiers) via your ✅ react!",
            color=discord.Color.green()
          )
          embed.set_footer(text="Note: You can use /settings to enable or disable these messages.")

          for tier in range(current_max_tier + 1):
            if tier in owned_tiers:
              symbol = "🔒" if tier in locked_tiers else "🔓"
              note = " (Locked)" if tier in locked_tiers else " (Unlocked)"
            else:
              symbol = "❌"
              note = ""
            embed.add_field(
              name=PRESTIGE_TIERS[tier],
              value=f"Owned: {symbol}{note}",
              inline=False
            )

          await member.send(embed=embed)
        except discord.Forbidden:
          logger.info(f"Unable to DM {member.display_name} about wishlist react update.")
    else:
      logger.info(f"{Style.BRIGHT}{member.display_name}{Style.RESET_ALL} removed a ✅ react from {Style.BRIGHT}{badge_name}{Style.RESET_ALL}")
      if badge_name in wished:
        logger.info(f"Removing {Style.BRIGHT}{badge_name}{Style.RESET_ALL} from wishlist via react")
        await db_remove_badge_info_id_from_wishlist(member.id, info['id'])
        try:
          # Fresh status
          instances = await db_get_user_badge_instances(payload.user_id, prestige=None)
          owned_tiers = {i['prestige_level'] for i in instances if i['badge_info_id'] == info['id'] and i['active']}
          locked_tiers = {i['prestige_level'] for i in instances if i['badge_info_id'] == info['id'] and i['active'] and i['locked']}
          echelon_progress = await db_get_echelon_progress(payload.user_id)
          current_max_tier = echelon_progress['current_prestige_tier']
          embed = discord.Embed(
            title="Badge Removed from Wishlist",
            description=f"**{badge_name}** has been removed from your Wishlist via your removal of the ✅ react!",
            color=discord.Color.green()
          )
          embed.set_footer(
            text="Note: You can use /settings to enable or disable these messages."
          )
          for tier in range(current_max_tier + 1):
            if tier in owned_tiers:
              symbol = "🔒" if tier in locked_tiers else "🔓"
              note = " (Locked)" if tier in locked_tiers else " (Unlocked)"
            else:
              symbol = "❌"
              note = ""
            embed.add_field(
              name=PRESTIGE_TIERS[tier],
              value=f"Owned: {symbol}{note}",
              inline=False
            )
          await member.send(embed=embed)
        except discord.Forbidden as e:
          logger.info(f"Unable to send wishlist remove react confirmation message to {member.display_name}, they have their DMs closed.")
          pass

  # ---------------------------------------------------------------------------
  # Cog helpers required by /wishlist matches, /wishlist dismissals, and the view
  # ---------------------------------------------------------------------------
  async def _purge_invalid_wishlist_dismissals(self, user_id: str, prestige_level: int):
    rows = await db_get_all_wishlist_dismissals(user_id)
    if not rows:
      return

    keep_prestige = int(prestige_level)
    wishlist = await db_get_simple_wishlist_badges(user_id)
    wishlist_ids = {int(b['badge_info_id']) for b in (wishlist or []) if str(b.get('badge_info_id', '')).isdigit()}

    # If wishlist is empty, clear all dismissals at this prestige for cleanliness.
    if not wishlist_ids:
      for r in rows:
        try:
          if int(r.get('prestige_level', -1)) != keep_prestige:
            continue
          pid = str(r.get('match_discord_id') or '')
          if not pid:
            continue
          await db_delete_wishlist_dismissal(user_id, pid, keep_prestige)
        except Exception:
          pass
      return

    # Remove rows whose badge_info_id is no longer on wishlist.
    for r in rows:
      try:
        if int(r.get('prestige_level', -1)) != keep_prestige:
          continue
        pid = str(r.get('match_discord_id') or '')
        if not pid:
          continue
        bid = int(r.get('badge_info_id'))
      except Exception:
        continue

      if bid not in wishlist_ids:
        pass

  async def _dismiss_partner_match(
    self,
    *,
    user_id: str,
    partner_id: str,
    prestige_level: int,
    has_ids: list[int],
    wants_ids: list[int]
  ):
    # IMPORTANT role mapping (matches your earlier semantics):
    # - has_ids = "badges_you_want_that_they_have" -> role='wants'
    # - wants_ids = "badges_they_want_that_you_have" -> role='has'
    p = int(prestige_level)

    # Dedup while preserving order
    has_ids = [int(x) for x in dict.fromkeys(has_ids or [])]
    wants_ids = [int(x) for x in dict.fromkeys(wants_ids or [])]

    for bid in has_ids:
      await db_add_wishlist_dismissal(
        user_id,
        partner_id,
        int(bid),
        p,
        'wants'
      )

    for bid in wants_ids:
      await db_add_wishlist_dismissal(
        user_id,
        partner_id,
        int(bid),
        p,
        'has'
      )

  async def _revoke_partner_dismissal(
    self,
    *,
    user_id: str,
    partner_id: str,
    prestige_level: int
  ):
    await db_delete_wishlist_dismissal(user_id, partner_id, int(prestige_level))


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
      embed.set_footer(text=f"Page {idx} of {len(pages_data)} ({len(wishes)} Badges Total)")
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
    name='matches',
    description='Find matches from other users who have what you want, and want what you have!'
  )
  @option(
    name='prestige',
    description='Which Prestige Tier to check',
    required=True,
    autocomplete=autocomplete_prestige_tiers
  )
  @commands.check(access_check)
  async def matches(self, ctx: discord.ApplicationContext, prestige: str):
    await ctx.defer(ephemeral=True)
    user_id = str(ctx.author.id)

    if not await is_prestige_valid(ctx, prestige):
      return
    prestige_level = int(prestige)

    await self._purge_invalid_wishlist_dismissals(user_id, prestige_level)

    wants = await db_get_active_wants(user_id, prestige_level)
    if not wants:
      await ctx.followup.send(
        embed=discord.Embed(
          title='Wishlist Complete',
          description=f"You have no {PRESTIGE_TIERS[prestige_level]} badges missing from your Wishlist.",
          color=discord.Color.green()
        ),
        ephemeral=True
      )
      return

    if await db_has_user_opted_out_of_prestige_matches(user_id, prestige_level):
      await ctx.followup.send(
        embed=discord.Embed(
          title='Matchmaking Disabled',
          description=(
            f"You have opted out of Wishlist matchmaking at the {PRESTIGE_TIERS[prestige_level]} tier.\n\n"
            "You may re-enable it via `/wishlist opt_out`."
          ),
          color=discord.Color.orange()
        ),
        ephemeral=True
      )
      return

    raw_matches = await db_get_wishlist_matches(user_id, prestige_level)

    opted_out_partners = set(await db_get_all_prestige_match_opted_out_user_ids(prestige_level))
    raw_matches = [m for m in (raw_matches or []) if str(m.get('match_discord_id')) not in opted_out_partners]

    partners = await _wishlist_build_matches_partner_dataset(
      bot=self.bot,
      user_id=user_id,
      prestige_level=prestige_level,
      matches=raw_matches or []
    )

    if not partners:
      await ctx.followup.send(
        embed=discord.Embed(
          title=f"No {PRESTIGE_TIERS[prestige_level]} Matches Found",
          description='No users currently have what you want and want what you have.',
          color=discord.Color.blurple()
        ),
        ephemeral=True
      )
      return

    view = WishlistPartnerView(
      cog=self,
      author_id=user_id,
      prestige_level=prestige_level,
      mode='matches',
      partners=partners
    )
    await view.start(ctx)


  # ________  .__               .__                      .__
  # \______ \ |__| ______ _____ |__| ______ ___________  |  |   ______
  #  |    |  \|  |/  ___//     \|  |/  ___//  ___/\__  \ |  |  /  ___/
  #  |    `   \  |\___ \|  Y Y  \  |\___ \ \___ \  / __ \|  |__\___ \
  # /_______  /__/____  >__|_|  /__/____  >____  >(____  /____/____  >
  #         \/        \/      \/        \/     \/      \/          \/
  @wishlist_group.command(
    name='dismissals',
    description='Review any wishlist matches which have been dismissed'
  )
  @option(
    name='prestige',
    description='Which Prestige Tier to check',
    required=True,
    autocomplete=autocomplete_prestige_tiers
  )
  @commands.check(access_check)
  async def dismissals(self, ctx: discord.ApplicationContext, prestige: str):
    await ctx.defer(ephemeral=True)
    user_id = str(ctx.author.id)

    if not await is_prestige_valid(ctx, prestige):
      return
    prestige_level = int(prestige)

    await self._purge_invalid_wishlist_dismissals(user_id, prestige_level)

    records = await db_get_all_wishlist_dismissals(user_id)
    recs = [r for r in (records or []) if int(r.get('prestige_level', -1)) == prestige_level]
    if not recs:
      await ctx.followup.send(
        embed=discord.Embed(
          title='No Wishlist Dismissals Found',
          description=f"You have no dismissed matches at the {PRESTIGE_TIERS[prestige_level]} tier.",
          color=discord.Color.green()
        ),
        ephemeral=True
      )
      return

    groups: dict[str, list[dict]] = {}
    for r in recs:
      pid = str(r.get('match_discord_id') or '')
      if not pid:
        continue
      groups.setdefault(pid, []).append(r)

    partners = await _wishlist_build_dismissals_partner_dataset(
      bot=self.bot,
      groups=groups
    )

    if not partners:
      await ctx.followup.send(
        embed=discord.Embed(
          title='No Active Members',
          description=(
            "You had one or more dismissals but the relevant member(s) are no longer active on the server. "
            "Their wishlist(s) have been cleared."
          ),
          color=discord.Color.orange()
        ),
        ephemeral=True
      )
      return

    view = WishlistPartnerView(
      cog=self,
      author_id=user_id,
      prestige_level=prestige_level,
      mode='dismissals',
      partners=partners
    )
    await view.start(ctx)


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

    instances = await db_get_user_badge_instances(user_discord_id, prestige=None)
    owned_tiers = {i['prestige_level'] for i in instances if i['badge_info_id'] == badge_info_id and i['active']}
    locked_tiers = {i['prestige_level'] for i in instances if i['badge_info_id'] == badge_info_id and i['active'] and i['locked']}

    echelon_progress = await db_get_echelon_progress(user_discord_id)
    current_max_tier = echelon_progress['current_prestige_tier']

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

    for tier in range(current_max_tier + 1):
      if tier in owned_tiers:
        symbol = "🔒" if tier in locked_tiers else "🔓"
        note = " (Locked)" if tier in locked_tiers else " (Unlocked)"
      else:
        symbol = "❌"
        note = ""
      embed.add_field(
        name=PRESTIGE_TIERS[tier],
        value=f"Owned: {symbol}{note}",
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

    embed = discord.Embed(
      title="Badge Removed Successfully",
      description=f"You've successfully removed `{badge_name}` from your wishlist",
      color=discord.Color.green()
    )

    instances = await db_get_user_badge_instances(user_discord_id, prestige=None)
    owned_tiers = {i['prestige_level'] for i in instances if i['badge_info_id'] == badge_info_id and i['active']}
    locked_tiers = {i['prestige_level'] for i in instances if i['badge_info_id'] == badge_info_id and i['active'] and i['locked']}

    echelon_progress = await db_get_echelon_progress(user_discord_id)
    current_max_tier = echelon_progress['current_prestige_tier']
    for tier in range(current_max_tier + 1):
      if tier in owned_tiers:
        symbol = "🔒" if tier in locked_tiers else "🔓"
        note = " (Locked)" if tier in locked_tiers else " (Unlocked)"
      else:
        symbol = "❌"
        note = ""
      embed.add_field(
        name=PRESTIGE_TIERS[tier],
        value=f"Owned: {symbol}{note}",
        inline=False
      )

    await ctx.followup.send(embed=embed)


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
    discord_file, attachment_url = await generate_unowned_badge_preview(user_discord_id, badge_info)

    embed = discord.Embed(
      title="Badge Locked Successfully",
      description=f"You've successfully locked `{badge_name}` from being listed in Wishlist matches (in the Prestige Tiers at which you possess it)!",
      color=discord.Color.green()
    )
    embed.set_image(url=attachment_url)

    instances = await db_get_user_badge_instances(user_discord_id, prestige=None)
    owned_tiers = {i['prestige_level'] for i in instances if i['badge_info_id'] == badge_info_id and i['active']}
    locked_tiers = {i['prestige_level'] for i in instances if i['badge_info_id'] == badge_info_id and i['active'] and i['locked']}

    echelon_progress = await db_get_echelon_progress(user_discord_id)
    current_max_tier = echelon_progress['current_prestige_tier']
    for tier in range(current_max_tier + 1):
      if tier in owned_tiers:
        symbol = "🔒" if tier in locked_tiers else "🔓"
        note = " (Locked)" if tier in locked_tiers else " (Unlocked)"
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
    discord_file, attachment_url = await generate_unowned_badge_preview(user_discord_id, badge_info)

    embed = discord.Embed(
      title="Badge Unlocked Successfully",
      description=f"You've successfully unlocked `{badge_name}` for Wishlist matching (in the Prestige Tiers at which you possess it)!",
      color=discord.Color.green()
    )
    embed.set_image(url=attachment_url)

    instances = await db_get_user_badge_instances(user_discord_id, prestige=None)
    owned_tiers = {i['prestige_level'] for i in instances if i['badge_info_id'] == badge_info_id and i['active']}
    locked_tiers = {i['prestige_level'] for i in instances if i['badge_info_id'] == badge_info_id and i['active'] and i['locked']}

    echelon_progress = await db_get_echelon_progress(user_discord_id)
    current_max_tier = echelon_progress['current_prestige_tier']
    for tier in range(current_max_tier + 1):
      if tier in owned_tiers:
        symbol = "🔒" if tier in locked_tiers else "🔓"
        note = " (Locked)" if tier in locked_tiers else " (Unlocked)"
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

#  __      __.__       .__    .__  .__          __ __________                __                     ____   ____.__
# /  \    /  \__| _____|  |__ |  | |__| _______/  |\______   \_____ ________/  |_  ____   __________\   \ /   /|__| ______  _  __
# \   \/\/   /  |/  ___/  |  \|  | |  |/  ___/\   __\     ___/\__  \\_  __ \   __\/    \_/ __ \_  __ \   Y   / |  |/ __ \ \/ \/ /
#  \        /|  |\___ \|   Y  \  |_|  |\___ \  |  | |    |     / __ \|  | \/|  | |   |  \  ___/|  | \/\     /  |  \  ___/\     /
#   \__/\  / |__/____  >___|  /____/__/____  > |__| |____|    (____  /__|   |__| |___|  /\___  >__|    \___/   |__|\___  >\/\_/
#        \/          \/     \/             \/                      \/                 \/     \/                        \/
class WishlistPartnerView(discord.ui.DesignerView):
  PAGE_SIZE = 30

  DETAILS_GIF_MATCHES = "https://i.imgur.com/3Xc47lK.gif"
  DETAILS_GIF_DISMISSALS = "https://i.imgur.com/ZAaiZKB.gif"
  HAS_GIF = "https://i.imgur.com/X446iF1.gif"
  WANTS_GIF = "https://i.imgur.com/X446iF1.gif"

  def __init__(
    self,
    *,
    cog,
    author_id: str,
    prestige_level: int,
    mode: str,
    partners: list[dict]
  ):
    super().__init__(timeout=360)

    self.cog = cog
    self.author_id = str(author_id)
    self.prestige_level = int(prestige_level)
    self.mode = mode  # "matches" | "dismissals"
    self.partners = partners or []

    self.partner_idx = 0
    self.tab = "details"  # "details" | "has" | "wants"
    self.page = 0

    self.message: discord.Message | None = None

    self._lock = asyncio.Lock()
    self._busy = False
    self._status: str | None = None

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    return str(interaction.user.id) == self.author_id

  def _log_exc(self, label: str):
    try:
      logger.exception(f"[wishlist.partner_view] {label}")
    except Exception:
      pass

  def _partner_overflow_count(self) -> int:
    return len(self.partners or [])

  def _build_fatal_error_container(self, *, title: str, text: str) -> discord.ui.Container:
    container = discord.ui.Container(color=discord.Color.red().value)
    container.add_item(discord.ui.TextDisplay(f"# {title}"))
    container.add_item(discord.ui.Separator())
    container.add_item(discord.ui.TextDisplay(text))
    return container

  async def _send_fatal_error(self, ctx: discord.ApplicationContext, *, title: str, text: str):
    try:
      self.clear_items()
    except Exception:
      pass

    self.add_item(self._build_fatal_error_container(title=title, text=text))

    try:
      already_done = bool(ctx.interaction and ctx.interaction.response and ctx.interaction.response.is_done())
      if already_done:
        self.message = await ctx.followup.send(view=self, ephemeral=True)
      else:
        await ctx.respond(view=self, ephemeral=True)
        try:
          self.message = await ctx.interaction.original_response()
        except Exception:
          self.message = None
    except Exception:
      self._log_exc("_send_fatal_error:send_failed")

    try:
      self.stop()
    except Exception:
      pass

  def _current_partner(self) -> dict | None:
    if not self.partners:
      return None
    if self.partner_idx < 0 or self.partner_idx >= len(self.partners):
      return None
    return self.partners[self.partner_idx]

  def _tier_name(self) -> str:
    try:
      return str(PRESTIGE_TIERS[self.prestige_level])
    except Exception:
      return "Unknown"

  def _title_block(self) -> str:
    if self.mode == "matches":
      return f"# Wishlist Matches (`{self._tier_name()}`)"
    return f"# Wishlist Dismissals (`{self._tier_name()}`)"

  def _get_total_pages_for_tab(self, tab: str) -> int:
    partner = self._current_partner()
    if not partner:
      return 1

    if tab == "has":
      n = len(partner.get("has_lines") or [])
    elif tab == "wants":
      n = len(partner.get("wants_lines") or [])
    else:
      return 1

    return max(1, math.ceil(n / self.PAGE_SIZE))

  def _wrap_state(self):
    if not self.partners:
      self.partner_idx = 0
      self.tab = "details"
      self.page = 0
      return

    if self.partner_idx < 0:
      self.partner_idx = len(self.partners) - 1
    if self.partner_idx >= len(self.partners):
      self.partner_idx = 0

    if self.tab not in ("details", "has", "wants"):
      self.tab = "details"
      self.page = 0

    total_pages = self._get_total_pages_for_tab(self.tab)
    if self.page < 0:
      self.page = total_pages - 1
    if self.page >= total_pages:
      self.page = 0

  def _slice_lines(self, lines: list[str], page: int) -> list[str]:
    start = page * self.PAGE_SIZE
    end = start + self.PAGE_SIZE
    return lines[start:end]

  def _build_partner_options(self) -> list[discord.SelectOption]:
    options = []
    for idx, p in enumerate(self.partners):
      label = p.get("partner_name") or "Unknown"
      desc = f"{len(p.get('has_lines') or [])} has / {len(p.get('wants_lines') or [])} wants"
      options.append(discord.SelectOption(
        label=str(label)[:100],
        description=str(desc)[:100],
        value=str(idx),
        default=(idx == self.partner_idx)
      ))
    return options[:25]

  def _build_tab_options(self) -> list[discord.SelectOption]:
    return [
      discord.SelectOption(label="Details", value="details", default=(self.tab == "details")),
      discord.SelectOption(label="What You Want", value="has", default=(self.tab == "has")),
      discord.SelectOption(label="What They Want", value="wants", default=(self.tab == "wants"))
    ]

  def _dismiss_help_text(self) -> str:
    if self.mode == "matches":
      return (
        "-# Press \"Dismiss Match\" below to hide this badge matchup.\n"
        "-# You may review your Dismissals with `/wishlist dismissals` to revoke the dismissal."
      )
    return "-# Use `Revoke Dismissal` to restore this Partner and matchup to `/wishlist matches`."

  def _add_gif_gallery(self, container: discord.ui.Container, url: str):
    container.add_gallery(
      discord.MediaGalleryItem(
        url=url,
        description="Mmm, flavor."
      )
    )

  def _details_gif(self) -> str:
    if self.mode == "dismissals":
      return self.DETAILS_GIF_DISMISSALS
    return self.DETAILS_GIF_MATCHES

  def _build_container(self) -> discord.ui.Container:
    self._wrap_state()

    container = discord.ui.Container(color=discord.Color.blurple().value)
    container.add_item(discord.ui.TextDisplay(self._title_block()))

    if self._status:
      container.add_item(discord.ui.Separator())
      container.add_item(discord.ui.TextDisplay(self._status))

    partner = self._current_partner()
    if not partner:
      container.add_item(discord.ui.Separator())
      container.add_item(discord.ui.TextDisplay(
        "## Nothing Left To Review\nAll partners have been cleared from this view.\n\n-# Session ended."
      ))
      return container

    container.add_item(discord.ui.Separator())
    if self.tab == "details":
      self._add_gif_gallery(container, self._details_gif())
    elif self.tab == "has":
      self._add_gif_gallery(container, self.HAS_GIF)
    elif self.tab == "wants":
      self._add_gif_gallery(container, self.WANTS_GIF)

    container.add_item(discord.ui.Separator())

    partner_select = discord.ui.Select(
      placeholder="Select a partner...",
      min_values=1,
      max_values=1,
      options=self._build_partner_options(),
      disabled=(len(self.partners) <= 1 or self._busy)
    )
    partner_select.callback = self._on_partner_select

    tab_select = discord.ui.Select(
      placeholder="Select a view...",
      min_values=1,
      max_values=1,
      options=self._build_tab_options(),
      disabled=self._busy
    )
    tab_select.callback = self._on_tab_select

    r1 = discord.ui.ActionRow()
    r1.add_item(partner_select)
    container.add_item(r1)

    r2 = discord.ui.ActionRow()
    r2.add_item(tab_select)
    container.add_item(r2)

    if self.tab == "details":
      partner_mention = partner.get("partner_mention") or f"<@{partner.get('partner_id')}>"

      has_total = len(partner.get("has_lines") or [])
      wants_total = len(partner.get("wants_lines") or [])

      has_label = "badge" if has_total == 1 else "badges"
      wants_label = "badge" if wants_total == 1 else "badges"

      container.add_item(discord.ui.Separator())
      container.add_item(discord.ui.TextDisplay(
        "\n".join([
          f"**Partner:** {partner_mention}",
          f"**What You Want:** {has_total} {has_label}",
          f"**What They Want:** {wants_total} {wants_label}",
          "",
          self._dismiss_help_text()
        ])
      ))

    if self.tab in ("has", "wants"):
      container.add_item(discord.ui.Separator())

      if self.tab == "has":
        title = "### Their Inventory"
        lines = partner.get("has_lines") or []
      else:
        title = "### Your Inventory"
        lines = partner.get("wants_lines") or []

      total_pages = self._get_total_pages_for_tab(self.tab)
      page_lines = self._slice_lines(lines, self.page)
      body = "\n".join(page_lines) if page_lines else "_No matching badges._"

      container.add_item(discord.ui.TextDisplay(f"{title}\n{body}"))

      if total_pages > 1:
        container.add_item(discord.ui.Separator())

        prev_disabled = (self.page <= 0)
        next_disabled = (self.page >= max(0, total_pages - 1))

        prev_btn = discord.ui.Button(
          label="Prev",
          style=discord.ButtonStyle.secondary,
          disabled=(prev_disabled or self._busy)
        )
        next_btn = discord.ui.Button(
          label="Next",
          style=discord.ButtonStyle.secondary,
          disabled=(next_disabled or self._busy)
        )
        page_btn = discord.ui.Button(
          label=f"Page {self.page + 1}/{total_pages}",
          style=discord.ButtonStyle.secondary,
          disabled=True
        )

        prev_btn.callback = self._on_prev
        next_btn.callback = self._on_next

        page_row = discord.ui.ActionRow()
        page_row.add_item(prev_btn)
        page_row.add_item(page_btn)
        page_row.add_item(next_btn)
        container.add_item(page_row)

        container.add_item(discord.ui.Separator())

    close_btn = discord.ui.Button(
      label="Close",
      style=discord.ButtonStyle.secondary,
      disabled=self._busy
    )

    action_label = "Dismiss Match" if self.mode == "matches" else "Revoke Dismissal"
    action_style = discord.ButtonStyle.danger if self.mode == "matches" else discord.ButtonStyle.primary
    action_btn = discord.ui.Button(
      label=action_label,
      style=action_style,
      disabled=self._busy
    )

    close_btn.callback = self._on_close
    action_btn.callback = self._on_action

    action_row = discord.ui.ActionRow()
    action_row.add_item(close_btn)
    action_row.add_item(action_btn)

    container.add_item(discord.ui.Separator())
    container.add_item(action_row)

    return container

  async def _rebuild(self):
    try:
      self.clear_items()
    except Exception:
      pass
    self.add_item(self._build_container())

  async def _edit_in_place(self, interaction: discord.Interaction):
    await self._rebuild()

    try:
      if not interaction.response.is_done():
        await interaction.response.edit_message(view=self)
        return
    except Exception:
      pass

    try:
      fn = getattr(interaction, "edit_original_response", None)
      if fn:
        await fn(view=self)
        return
    except Exception:
      pass

    try:
      if interaction.message:
        await interaction.message.edit(view=self)
        return
    except Exception:
      pass

    try:
      if self.message:
        await self.message.edit(view=self)
        return
    except Exception:
      self._log_exc("_edit_in_place:all_failed")

  async def start(self, ctx: discord.ApplicationContext):
    if self._partner_overflow_count() > 25:
      try:
        raise RuntimeError(
          f"WishlistPartnerView partner overflow: count={self._partner_overflow_count()} "
          f"mode={self.mode} author_id={self.author_id} prestige_level={self.prestige_level}"
        )
      except Exception:
        self._log_exc("partner_overflow")

      await self._send_fatal_error(
        ctx,
        title="Too Many Matches",
        text=(
          "You have more than 25 partners in this list, which exceeds the Discord dropdown limit.\n\n"
          "Nothing is broken, this view just cannot display that many partners yet.\n"
          "-# Please report this so we can prioritize the fix."
        )
      )
      return

    try:
      await self._rebuild()
    except Exception:
      self._log_exc("start:_rebuild")
      return

    try:
      already_done = bool(ctx.interaction and ctx.interaction.response and ctx.interaction.response.is_done())
      if already_done:
        self.message = await ctx.followup.send(view=self, ephemeral=True)
      else:
        await ctx.respond(view=self, ephemeral=True)
        try:
          self.message = await ctx.interaction.original_response()
        except Exception:
          self.message = None
    except Exception:
      self._log_exc("start:send")

  async def on_timeout(self):
    try:
      self.disable_all_items()
    except Exception:
      pass

    try:
      if self.message:
        await self.message.edit(view=self)
    except Exception:
      pass

    try:
      self.stop()
    except Exception:
      pass

  async def _run_state_change(self, interaction: discord.Interaction, fn):
    async with self._lock:
      await fn()
      await self._edit_in_place(interaction)

  async def _run_db_action(self, interaction: discord.Interaction, fn, *, status: str):
    async with self._lock:
      self._busy = True
      self._status = status
      await self._edit_in_place(interaction)

      try:
        await fn()
      finally:
        self._status = None
        self._busy = False
        await self._edit_in_place(interaction)

  async def _show_final_message(self, interaction: discord.Interaction, *, title: str, text: str):
    async with self._lock:
      try:
        self.clear_items()
      except Exception:
        pass

      container = discord.ui.Container(color=discord.Color.blurple().value)
      container.add_item(discord.ui.TextDisplay(f"# {title}"))
      container.add_item(discord.ui.Separator())
      container.add_item(discord.ui.TextDisplay(text))
      self.add_item(container)

      try:
        if not interaction.response.is_done():
          await interaction.response.edit_message(view=self)
        else:
          fn = getattr(interaction, "edit_original_response", None)
          if fn:
            await fn(view=self)
          elif interaction.message:
            await interaction.message.edit(view=self)
          elif self.message:
            await self.message.edit(view=self)
      except Exception:
        self._log_exc("_show_final_message:edit_failed")

      try:
        self.stop()
      except Exception:
        pass

  async def _on_partner_select(self, interaction: discord.Interaction):
    async def _do():
      try:
        vals = (interaction.data or {}).get("values") or []
        self.partner_idx = int(vals[0]) if vals else 0
      except Exception:
        self.partner_idx = 0

      self.tab = "details"
      self.page = 0

    await self._run_state_change(interaction, _do)

  async def _on_tab_select(self, interaction: discord.Interaction):
    async def _do():
      try:
        vals = (interaction.data or {}).get("values") or []
        self.tab = vals[0] if vals else "details"
      except Exception:
        self.tab = "details"

      self.page = 0

    await self._run_state_change(interaction, _do)

  async def _on_prev(self, interaction: discord.Interaction):
    async def _do():
      self.page = max(0, self.page - 1)
    await self._run_state_change(interaction, _do)

  async def _on_next(self, interaction: discord.Interaction):
    async def _do():
      total_pages = self._get_total_pages_for_tab(self.tab)
      self.page = min(total_pages - 1, self.page + 1)
    await self._run_state_change(interaction, _do)

  async def _on_action(self, interaction: discord.Interaction):
    partner = self._current_partner()
    if not partner:
      try:
        if not interaction.response.is_done():
          await interaction.response.defer(invisible=True)
      except Exception:
        pass
      return

    if self.mode == "matches":
      partner_mention = partner.get("partner_mention") or f"<@{partner.get('partner_id')}>"

      async def _do():
        await self.cog._dismiss_partner_match(
          user_id=self.author_id,
          partner_id=str(partner.get("partner_id")),
          prestige_level=self.prestige_level,
          has_ids=partner.get("has_ids") or [],
          wants_ids=partner.get("wants_ids") or []
        )

      await self._run_db_action(interaction, _do, status="Saving...")
      await self._show_final_message(
        interaction,
        title="Match Dismissed",
        text=f"Your match with {partner_mention} has been dismissed successfully."
      )
      return

    async def _do():
      await self.cog._revoke_partner_dismissal(
        user_id=self.author_id,
        partner_id=str(partner.get("partner_id")),
        prestige_level=self.prestige_level
      )

      try:
        self.partners.pop(self.partner_idx)
      except Exception:
        self.partners = [p for i, p in enumerate(self.partners) if i != self.partner_idx]

      if self.partner_idx >= len(self.partners):
        self.partner_idx = max(0, len(self.partners) - 1)

      self.tab = "details"
      self.page = 0

    await self._run_db_action(interaction, _do, status="Saving...")

  async def _on_close(self, interaction: discord.Interaction):
    async with self._lock:
      try:
        if not interaction.response.is_done():
          try:
            await interaction.response.defer(invisible=True)
          except Exception:
            pass
      except Exception:
        pass

      msg = interaction.message or self.message
      try:
        if msg:
          await msg.delete()
      except Exception:
        try:
          await interaction.delete_original_response()
        except Exception:
          pass

      try:
        self.stop()
      except Exception:
        pass
