from common import *
from handlers.xp import grant_xp
from handlers.eschelon_xp import *
from queries.badge_info import *
from queries.badge_instances import *
from queries.crystal_instances import *

from utils.crystal_effects import delete_crystal_effects_cache
from utils.crystal_instances import *
from utils.eschelon_rewards import *

class Admin(commands.Cog):
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
      if b['id'] in owned_badge_info_ids and ctx.value.lower() in b['badge_name'].lower()
    ]
    return filtered

  async def autocomplete_crystals(self, ctx: discord.AutocompleteContext):
    crystals = await db_get_available_crystal_types()
    results = []
    for c in crystals:
      label = f"{c['emoji']} {c['name']}"
      results.append(discord.OptionChoice(name=label, value=str(c['id'])))
    return results

  admin_group = discord.SlashCommandGroup("admin", "Admin Commands for Debugging.")

  @admin_group.command(name="crystallize", description="Attach a crystal to a user's badge")
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
    "crystal",
    str,
    description="Crystal Type",
    required=True,
    autocomplete=autocomplete_crystals,
    max_length=128
  )
  async def crystallize(self, ctx, user: discord.User, badge_name: str, crystal: str):
    await ctx.defer(ephemeral=True)
    crystal_type_id = int(crystal)

    # Step 1: Get the badge info
    badge_info = await db_get_badge_info_by_name(badge_name)
    if not badge_info:
      embed = discord.Embed(title="Badge Not Found", description=f"❌ Could not find badge with name '{badge_name}'", color=discord.Color.red())
      return await ctx.respond(embed=embed, ephemeral=True)

    # Step 2: Get the instance
    instance = await db_get_badge_instance_by_badge_info_id(user.id, badge_info['id'])
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


  @admin_group.command(name="grant_pattern_buffer", description="Grant Crystal Pattern Buffers to a user.")
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
        f"✨ Granted Replicator Pattern Buffers to {user.mention}.\n\n"
        f"They now have **{new_total}** total."
      ),
      color=discord.Color.blue()
    )
    await ctx.respond(embed=embed, ephemeral=True)

  @admin_group.command(name="clear_effects_cache", description="Clear the crystal effects cache")
  async def clear_effects_cache(self, ctx):
    delete_crystal_effects_cache()
    embed = discord.Embed(
      title="Crystal Effects Cache Cleared",
      description="🧹 All cached crystal effect images have been deleted.",
      color=discord.Color.orange()
    )
    await ctx.respond(embed=embed, ephemeral=True)

  @admin_group.command(name="eschelon_view", description="View a user's Eschelon XP/level info.")
  @option("user", discord.User, description="The user to view.", required=True)
  async def eschelon_view(self, ctx, user: discord.User):
    await ctx.defer(ephemeral=True)

    progress = await db_get_eschelon_progress(user.id)
    if not progress:
      embed = discord.Embed(title="User Not Found", description=f"❌ {user.mention} has no Eschelon data.", color=discord.Color.red())
      return await ctx.respond(embed=embed, ephemeral=True)

    embed = discord.Embed(
      title=f"Eschelon Progress for {user.display_name}",
      description=(
        f"**Level:** {progress['current_level']}\n"
        f"**XP:** {progress['current_xp']}\n"
        f"**Buffer Failure Streak:** {progress['buffer_failure_streak']}"
      ),
      color=discord.Color.blue()
    )
    await ctx.respond(embed=embed, ephemeral=True)

  @admin_group.command(name="eschelon_award_xp", description="Award XP to a user.")
  @option("user", discord.User, description="The user to award XP.", required=True)
  @option("amount", int, description="XP amount.", required=True, min_value=1, max_value=10000)
  async def eschelon_award_xp(self, ctx, user: discord.User, amount: int):
    await ctx.defer(ephemeral=True)

    await award_xp(user, amount, "admin")

    embed = discord.Embed(
      title="XP Awarded",
      description=f"✅ Granted **{amount} XP** to {user.mention}.",
      color=discord.Color.green()
    )
    await ctx.respond(embed=embed, ephemeral=True)

  @admin_group.command(name="eschelon_set_level", description="Force a user's level.")
  @option("user", discord.User, description="The user.", required=True)
  @option("level", int, description="Target level.", required=True, min_value=1, max_value=9999)
  async def eschelon_set_level(self, ctx, user: discord.User, level: int):
    await ctx.defer(ephemeral=True)

    xp_required = sum(xp_required_for_level(lvl) for lvl in range(1, level))
    await force_set_xp(user.id, xp_required, "admin")

    embed = discord.Embed(
      title="Level Set",
      description=f"✅ Set {user.mention} to Level **{level}** (Total XP: {xp_required}).",
      color=discord.Color.orange()
    )
    await ctx.respond(embed=embed, ephemeral=True)

  @admin_group.command(name="eschelon_reset_buffer_streak", description="Reset user's buffer streak.")
  @option("user", discord.User, description="The user.", required=True)
  async def eschelon_reset_buffer_streak(self, ctx, user: discord.User):
    await ctx.defer(ephemeral=True)

    await db_update_buffer_failure_streak(user.id, 0)

    embed = discord.Embed(
      title="Buffer Streak Reset",
      description=f"🔄 Reset buffer failure streak for {user.mention}.",
      color=discord.Color.teal()
    )
    await ctx.respond(embed=embed, ephemeral=True)

  @admin_group.command(name="eschelon_view_buffer_streak", description="View user's buffer streak.")
  @option("user", discord.User, description="The user.", required=True)
  async def eschelon_view_buffer_streak(self, ctx, user: discord.User):
    await ctx.defer(ephemeral=True)

    progress = await db_get_eschelon_progress(user.id)
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

  @admin_group.command(name="eschelon_force_buffer_roll", description="Force a crystal buffer roll.")
  @option("user", discord.User, description="The user.", required=True)
  async def eschelon_force_buffer_roll(self, ctx, user: discord.User):
    await ctx.defer(ephemeral=True)

    success = await award_possible_crystal_buffer_pattern(user)
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

  @admin_group.command(name="eschelon_simulate_near_level_up", description="Force a (near) level-up process.")
  @option("user", discord.User, description="The user.", required=True)
  async def eschelon_simulate_near_level_up(self, ctx, user: discord.User):
    await ctx.defer(ephemeral=True)

    progress = await db_get_eschelon_progress(user.id)
    xp_needed = xp_required_for_level(progress['current_level']) if progress else 69

    await grant_xp(user, xp_needed - 1, reason="admin")

    embed = discord.Embed(
      title="Level-Up Near-Simulated",
      description=f"🎖️ Near-Simulated a full Eschelon level-up for {user.mention}. They are 1xp away from leveling up now.",
      color=discord.Color.gold()
    )
    await ctx.respond(embed=embed, ephemeral=True)
