from common import *
from queries.badge_info import db_get_badge_info_by_name, db_get_all_badge_info
from queries.badge_inventory import db_get_badge_instance, db_get_user_badges
from queries.crystals import db_attach_crystal_to_instance, db_get_available_crystal_types

class Admin(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @commands.slash_command(name="crystallize", description="Attach a crystal to a user's badge")
  async def crystallize(
    self,
    ctx,
    user: discord.User,
    badge_name: str,
    crystal_name: str
  ):
    await ctx.defer(ephemeral=True)

    # Step 1: Get the badge info
    badge_info = await db_get_badge_info_by_name(badge_name)
    if not badge_info:
      embed = discord.Embed(title="Badge Not Found", description=f"❌ Could not find badge with name '{badge_name}'", color=discord.Color.red())
      await ctx.respond(embed=embed, ephemeral=True)
      return

    # Step 2: Find the instance
    instance = await db_get_badge_instance(user.id, badge_info['id'])
    if not instance:
      embed = discord.Embed(title="Instance Missing", description=f"❌ {user.mention} does not have a badge instance for '{badge_name}'", color=discord.Color.red())
      await ctx.respond(embed=embed, ephemeral=True)
      return

    # Step 3: Attach crystal
    crystal = await db_attach_crystal_to_instance(instance['id'], crystal_name=crystal_name)
    if not crystal:
      embed = discord.Embed(title="Duplicate Crystal", description=f"⚠️ Crystal '{crystal_name}' already exists on this instance.", color=discord.Color.red())
      await ctx.respond(embed=embed, ephemeral=True)
      return

    embed = discord.Embed(
      title="Crystal Attached",
      description=f"✅ Attached **{crystal_name}** to {user.mention}'s **{badge_name}**.",
      color=discord.Color.red()
    )
    await ctx.respond(embed=embed, ephemeral=True)

  @crystallize.autocomplete("badge_name")
  async def autocomplete_badge_name(self, ctx: discord.AutocompleteContext):
    user = ctx.options.get("user")
    user_id = user.id if user else None
    if not user_id:
      return []

    all_badges = await db_get_all_badge_info()
    owned_badges = await db_get_user_badges(user_id)
    owned_badge_ids = {b['id'] for b in owned_badges}

    filtered = [b['badge_name'] for b in all_badges if b['id'] in owned_badge_ids and ctx.value.lower() in b['badge_name'].lower()]
    return filtered[:20]

  @crystallize.autocomplete("crystal_name")
  async def autocomplete_crystal_name(self, ctx: discord.AutocompleteContext):
    crystals = await db_get_available_crystal_types()
    return [c['name'] for c in crystals if ctx.value.lower() in c['name'].lower()][:20]
