from collections import defaultdict
from pymysql.err import IntegrityError

from common import *
from handlers.xp import grant_xp
from handlers.echelon_xp import *
from queries.debug import *
from queries.badge_info import *
from queries.badge_instances import *
from queries.crystal_instances import *

from utils.crystal_effects import delete_crystal_effects_cache
from utils.crystal_instances import *
from utils.echelon_rewards import *
from utils.string_utils import strip_bullshit

class Debug(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  async def autocomplete_badge_name(self, ctx: discord.AutocompleteContext):
    user_id = ctx.options.get("user")
    if not user_id:
      return []

    all_badges = await db_get_all_badge_info()
    owned_badges = await db_get_user_badge_instances(user_id)
    owned_badge_info_ids = {b['badge_info_id'] for b in owned_badges}

    filtered = [
      b['badge_name']
      for b in all_badges
      if b['id'] in owned_badge_info_ids and strip_bullshit(ctx.value.lower()) in strip_bullshit(b['badge_name'].lower())
    ]
    return filtered

  async def autocomplete_crystals(self, ctx: discord.AutocompleteContext):
    crystals = await db_get_available_crystal_types()
    results = []
    results = []
    for c in crystals:
      label = f"{c['emoji']} {c['name']}"
      if strip_bullshit(ctx.value.lower()) in strip_bullshit(c['name'].lower()):
        results.append(discord.OptionChoice(name=label, value=str(c['id'])))
    return results


  async def autocomplete_crystal_rarities(ctx: discord.AutocompleteContext):
    rarities = await db_get_crystal_rarity_weights()
    return [
      discord.OptionChoice(name=r['rarity_rank'].capitalize(), value=str(r['rarity_rank']))
      for r in sorted(rarities, key=lambda r: r['rarity_rank'])
    ]

  async def autocomplete_crystals_by_rarity(ctx: discord.AutocompleteContext):
    rarity_rank = ctx.options.get("rarity")
    if not rarity_rank or not rarity_rank.isdigit():
      return [discord.OptionChoice(name="🔒 Select a Rarity First", value="none")]

    crystals = await db_get_crystals_by_rarity(int(rarity_rank))
    filtered = [
      c for c in crystals
      if strip_bullshit(ctx.value.lower()) in strip_bullshit(c['name'].lower())
    ]
    return [
      discord.OptionChoice(name=f"{c.get('emoji', '')} {c['name']}", value=str(c['id']))
      for c in filtered[:25]
    ]

  debug_group = discord.SlashCommandGroup("debug", "Admin Commands for Debugging.")

  @debug_group.command(name="crystallize", description="Attach a crystal to a user's badge")
  @option(
    "user",
    discord.User,
    description="The user whose inventory you wish to crystallize",
    required=True
  )
  @option(
    "badge_name",
    str,
    description="Badge Name",
    required=True,
    autocomplete=autocomplete_badge_name,
    max_length=128
  )
  @option(
    "prestige",
    int,
    description="Prestige Tier",
    required=True,
    choices=[
      discord.OptionChoice(name=label, value=str(tier))
      for tier, label in PRESTIGE_TIERS.items()
    ]
  )
  @option(
    "crystal",
    str,
    description="Crystal Type",
    required=True,
    autocomplete=autocomplete_crystals,
    max_length=128
  )
  async def crystallize(self, ctx, user: discord.User, badge_name: str, prestige: str, crystal: str):
    await ctx.defer(ephemeral=True)
    prestige = int(prestige)
    crystal_type_id = int(crystal)

    # Step 1: Get the badge info
    badge_info = await db_get_badge_info_by_name(badge_name)
    if not badge_info:
      embed = discord.Embed(title="Badge Not Found", description=f"❌ Could not find badge with name '{badge_name}'", color=discord.Color.red())
      return await ctx.respond(embed=embed, ephemeral=True)

    # Step 2: Get the instance
    instance = await db_get_badge_instance_by_badge_info_id(user.id, badge_info['id'], prestige=prestige)
    if not instance:
      embed = discord.Embed(title="Instance Missing", description=f"❌ {user.mention} does not have a badge instance for '{badge_name}'", color=discord.Color.red())
      return await ctx.respond(embed=embed, ephemeral=True)

    # Step 3: Create and attach the crystal
    crystal = await create_new_crystal_instance(user.id, crystal_type_id)
    if not crystal:
      embed = discord.Embed(title="Unable to Create Crystal Instance", description="⚠️ Something went wrong when trying to create the crystal instance.", color=discord.Color.red())
      return await ctx.respond(embed=embed, ephemeral=True)

    await attune_crystal_to_badge(crystal['crystal_instance_id'], instance['badge_instance_id'])

    embed = discord.Embed(
      title="Crystal Attached",
      description=f"✅ Attached **{crystal['crystal_name']}** to {user.mention}'s **{badge_name}**.",
      color=discord.Color.green()
    )
    await ctx.respond(embed=embed, ephemeral=True)


  @debug_group.command(name="grant_pattern_buffer", description="Grant Crystal Pattern Buffers to a user.")
  @option(
    "user",
    discord.User,
    description="The user who should receive the buffer(s).",
    required=True
  )
  @option(
    "amount",
    int,
    description="Set a specific number (if omitted will just increment)",
    required=False,
    min_value=1,
    max_value=100
  )
  async def grant_pattern_buffer(self, ctx, user: discord.User, amount: int = None):
    await ctx.defer(ephemeral=True)

    if amount:
      await db_set_user_crystal_buffer(user.id, amount)
    else:
      await db_increment_user_crystal_buffer(user.id)

    new_total = await db_get_user_crystal_buffer_count(user.id)

    embed = discord.Embed(
      title="Pattern Buffer(s) Granted",
      description=(
        f"✨ Granted Crystal Pattern Buffers to {user.mention}.\n\n"
        f"They now have **{new_total}** total."
      ),
      color=discord.Color.green()
    )
    await ctx.respond(embed=embed, ephemeral=True)

  @debug_group.command(name="grant_unattached_crystals", description="(DEBUG) Grant unattuned Crystal(s) to a user.")
  @option("user", discord.User, description="User to receive crystal(s)", required=True)
  @option("rarity", str, description="Rarity of the Crystal", required=True, autocomplete=autocomplete_crystal_rarities)
  @option("crystal", int, description="Crystal Type to grant", required=True, autocomplete=autocomplete_crystals_by_rarity)
  @option("amount", int, description="Number of crystals to grant", required=True, min_value=1, max_value=50)
  async def grant_unattached_crystals(self, ctx, user: discord.User, rarity: str, crystal: int, amount: int):
    await ctx.defer(ephemeral=True)

    crystal_type = await db_get_crystal_by_type_id(crystal)
    if not crystal_type:
      return await ctx.respond(
        embed=discord.Embed(
          title="❌ Invalid Crystal Type",
          description="Could not locate that crystal type.",
          color=discord.Color.red()
        ),
        ephemeral=True
      )

    for _ in range(amount):
      await create_new_crystal_instance(user.id, crystal_type['id'])

    embed = discord.Embed(
      title="✅ Crystals Granted",
      description=(
        f"Granted **{amount}**x unattuned {crystal_type['emoji']} **{crystal_type['name']}** crystal(s)\n"
        f"to {user.mention} (Rarity: *{crystal_type['rarity_name']}*)"
      ),
      color=discord.Color.green()
    )
    await ctx.respond(embed=embed, ephemeral=True)

  @debug_group.command(name="echelon_view", description="View a user's Echelon XP/level info.")
  @option("user", discord.User, description="The user to view.", required=True)
  async def echelon_view(self, ctx, user: discord.User):
    await ctx.defer(ephemeral=True)

    progress = await db_get_echelon_progress(user.id)
    if not progress:
      embed = discord.Embed(title="User Not Found", description=f"❌ {user.mention} has no Echelon data.", color=discord.Color.red())
      return await ctx.respond(embed=embed, ephemeral=True)

    embed = discord.Embed(
      title=f"Echelon Progress for {user.display_name}",
      description=(
        f"**Level:** {progress['current_level']}\n"
        f"**XP:** {progress['current_xp']}\n"
        f"**Buffer Failure Streak:** {progress['buffer_failure_streak']}"
      ),
      color=discord.Color.blue()
    )
    await ctx.respond(embed=embed, ephemeral=True)

  @debug_group.command(name="echelon_award_xp", description="Award XP to a user.")
  @option("user", discord.User, description="The user to award XP.", required=True)
  @option("amount", int, description="XP amount.", required=True, min_value=1, max_value=10000)
  async def echelon_award_xp(self, ctx, user: discord.User, amount: int):
    await ctx.defer(ephemeral=True)

    await award_xp(user, amount, "admin")

    embed = discord.Embed(
      title="XP Awarded",
      description=f"✅ Granted **{amount} XP** to {user.mention}.",
      color=discord.Color.green()
    )
    await ctx.respond(embed=embed, ephemeral=True)

  @debug_group.command(name="echelon_set_level", description="Force a user's level.")
  @option("user", discord.User, description="The user.", required=True)
  @option("level", int, description="Target level.", required=True, min_value=1, max_value=9999)
  async def echelon_set_level(self, ctx, user: discord.User, level: int):
    await ctx.defer(ephemeral=True)

    xp_required = sum(xp_required_for_level(lvl) for lvl in range(1, level))
    await force_set_xp(user.id, xp_required, "admin")

    embed = discord.Embed(
      title="Level Set",
      description=f"✅ Set {user.mention} to Level **{level}** (Total XP: {xp_required}).",
      color=discord.Color.orange()
    )
    await ctx.respond(embed=embed, ephemeral=True)

  @debug_group.command(name="echelon_reset_buffer_streak", description="Reset user's buffer streak.")
  @option("user", discord.User, description="The user.", required=True)
  async def echelon_reset_buffer_streak(self, ctx, user: discord.User):
    await ctx.defer(ephemeral=True)

    await db_update_buffer_failure_streak(user.id, 0)

    embed = discord.Embed(
      title="Buffer Streak Reset",
      description=f"🔄 Reset buffer failure streak for {user.mention}.",
      color=discord.Color.teal()
    )
    await ctx.respond(embed=embed, ephemeral=True)

  @debug_group.command(name="echelon_view_buffer_streak", description="View user's buffer streak.")
  @option("user", discord.User, description="The user.", required=True)
  async def echelon_view_buffer_streak(self, ctx, user: discord.User):
    await ctx.defer(ephemeral=True)

    progress = await db_get_echelon_progress(user.id)
    streak = progress['buffer_failure_streak'] if progress else 0
    if streak >= 5:
      chance = 100.0
    else:
      chance = min(100.0, 20.0 + (streak ** 2) * 3.75)

    embed = discord.Embed(
      title=f"Buffer Streak for {user.display_name}",
      description=f"**Failure Streak:** {streak}\n**Next Roll Chance:** {chance:.1f}%",
      color=discord.Color.blurple()
    )
    await ctx.respond(embed=embed, ephemeral=True)

  @debug_group.command(name="echelon_force_buffer_roll", description="Force a crystal buffer roll.")
  @option("user", discord.User, description="The user.", required=True)
  async def echelon_force_buffer_roll(self, ctx, user: discord.User):
    await ctx.defer(ephemeral=True)

    success = await award_possible_crystal_pattern_buffer(user)
    if success:
      message = f"✨ {user.mention} **successfully** received a Pattern Buffer!"
      color = discord.Color.green()
    else:
      message = f"⚡ {user.mention} did **not** receive a Pattern Buffer this time."
      color = discord.Color.red()

    embed = discord.Embed(
      title="Buffer Roll Attempt",
      description=message,
      color=color
    )
    await ctx.respond(embed=embed, ephemeral=True)

  @debug_group.command(name="echelon_simulate_level_up", description="Force a (near) level-up process.")
  @option("user", discord.User, description="The user.", required=True)
  async def echelon_simulate_level_up(self, ctx, user: discord.User):
    await ctx.defer(ephemeral=True)

    progress = await db_get_echelon_progress(user.id)
    xp_needed = 69 # default just in case

    if progress:
      level, xp_into_level, xp_required = xp_progress_within_level(progress['current_xp'])
      xp_needed = xp_required - xp_into_level

    await grant_xp(user, xp_needed, reason="admin")

    embed = discord.Embed(
      title="Level-Up Simulated",
      description=f"🎖️ Simulated a full Echelon level-up for {user.mention}. They should have leveled up now(?)",
      color=discord.Color.gold()
    )
    await ctx.respond(embed=embed, ephemeral=True)


  @debug_group.command(name="echelon_simulate_near_level_up", description="Force a (near) level-up process.")
  @option("user", discord.User, description="The user.", required=True)
  async def echelon_simulate_near_level_up(self, ctx, user: discord.User):
    await ctx.defer(ephemeral=True)

    progress = await db_get_echelon_progress(user.id)
    xp_needed = xp_required_for_level(progress['current_level']) if progress else 69

    await grant_xp(user, xp_needed - 5, reason="admin")

    embed = discord.Embed(
      title="Level-Up Near-Simulated",
      description=f"🎖️ Near-Simulated a full Echelon level-up for {user.mention}. They are 1xp away from leveling up now.",
      color=discord.Color.gold()
    )
    await ctx.respond(embed=embed, ephemeral=True)

  @debug_group.command(name="echelon_grant_prestige_badges", description="Grant random non-duplicate badges at a specific prestige level.")
  @option("user", discord.User, description="The user to receive badges.", required=True)
  @option(
    "prestige",
    int,
    description="Prestige Tier",
    required=True,
    choices=[
      discord.OptionChoice(name=label, value=str(tier))
      for tier, label in PRESTIGE_TIERS.items()
    ]
  )
  @option("amount", int, description="How many unique badges to grant.", required=True, min_value=1, max_value=999)
  async def echelon_grant_prestige_badges(self, ctx, user: discord.User, prestige: str, amount: int):
    await ctx.defer(ephemeral=True)

    prestige = int(prestige)
    working_embed = discord.Embed(
      title="Granting Badges...",
      description=f"Processing badge grants for {user.mention} at **{PRESTIGE_TIERS[prestige]}**...",
      color=discord.Color.dark_gold()
    )
    message = await ctx.respond(embed=working_embed, ephemeral=True)

    all_badges = await db_get_all_badge_info()
    owned_instances = await db_get_user_badge_instances(user.id)
    owned_by_prestige: dict[int, set[int]] = defaultdict(set)
    for b in owned_instances:
      owned_by_prestige[b['prestige_level']].add(b['badge_info_id'])

    available = [b for b in all_badges if b['id'] not in owned_by_prestige.get(prestige, set())]
    if not available:
      await ctx.respond(embed=discord.Embed(
        title="No Available Badges",
        description=f"{user.mention} already owns every badge at **{PRESTIGE_TIERS[prestige]}**!",
        color=discord.Color.red()
      ))
      return

    random.shuffle(available)
    granted = []
    attempted_ids = set()

    while available and len(granted) < amount:
      badge = available.pop()
      badge_id = badge['id']

      if badge_id in attempted_ids:
        continue
      attempted_ids.add(badge_id)

      try:
        instance = await create_new_badge_instance(user.id, badge_id, prestige)
      except IntegrityError as e:
        if "Duplicate entry" in str(e):
          continue  # Already granted somehow, skip silently
        raise  # Bubble up anything else

      if instance:
        granted.append(badge['badge_name'])
        owned_by_prestige[prestige].add(badge_id)

    embed = discord.Embed(
      title="Badges Granted",
      description=f"✅ Gave {len(granted)} unique badge(s) to {user.mention} at **{PRESTIGE_TIERS[prestige]}**.",
      color=discord.Color.green()
    )
    await message.edit(embed=embed)

  @debug_group.command(name="echelon_purge_prestige_badges", description="Remove all badge instances from a user at a specific prestige level.")
  @option("user", discord.User, description="The user to purge badges from.", required=True)
  @option(
    "prestige",
    int,
    description="Prestige Tier",
    required=True,
    choices=[discord.OptionChoice(name=label, value=str(tier)) for tier, label in PRESTIGE_TIERS.items()]
  )
  async def echelon_purge_prestige_badges(self, ctx, user: discord.User, prestige: str):
    await ctx.defer(ephemeral=True)
    prestige = int(prestige)

    deleted = await db_orphan_badge_instances_by_prestige(user.id, prestige)

    embed = discord.Embed(
      title="Badges Orphaned",
      description=f"🗑️ Orphaned **{deleted}** badge(s) from {user.mention} at **{PRESTIGE_TIERS[prestige]}**.",
      color=discord.Color.red()
    )
    await ctx.respond(embed=embed, ephemeral=True)

  @debug_group.command(name="echelon_pqif_status", description="Check PQIF status for a user across all prestige levels.")
  @option("user", discord.User, description="User to inspect.", required=True)
  async def echelon_pqif_status(self, ctx, user: discord.User):
    await ctx.defer(ephemeral=True)

    all_badges = await db_get_all_badge_info()
    total_badge_count = len(all_badges)

    lines = []
    for prestige_level, label in PRESTIGE_TIERS.items():
      user_badges = await db_get_user_badge_instances(user.id, prestige=prestige_level)
      owned_count = len(user_badges)
      percentage = owned_count / total_badge_count * 100 if total_badge_count > 0 else 0

      in_field = await is_user_within_pqif(user, prestige_level)
      field_status = "🟢 **IN FIELD**" if in_field else "⚪ Outside"

      lines.append(
        f"**{label}**: {owned_count}/{total_badge_count} badges ({percentage:.1f}%) → {field_status}"
      )

    embed = discord.Embed(
      title=f"PQIF Scan for {user.display_name}",
      description="\n".join(lines),
      color=discord.Color.blurple()
    )
    await ctx.respond(embed=embed, ephemeral=True)
