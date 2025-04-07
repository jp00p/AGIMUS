from common import *
from queries.badge_info import db_get_badge_info_by_name, db_get_all_badge_info
from queries.badge_inventory import db_get_badge_instance, db_get_user_badges
from queries.crystals import db_attach_crystal_to_instance, db_get_available_crystal_types

class Admin(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  async def autocomplete_badge_name(self, ctx: discord.AutocompleteContext):
    user_id = ctx.options.get("user")
    logger.info(user_id)
    if not user_id:
      return []

    all_badges = await db_get_all_badge_info()
    owned_badges = await db_get_user_badges(user_id)
    owned_badge_ids = {b['id'] for b in owned_badges}

    filtered = [b['badge_name'] for b in all_badges if b['id'] in owned_badge_ids and ctx.value.lower() in b['badge_name'].lower()]
    return filtered[:25]

  async def autocomplete_crystal_name(self, ctx: discord.AutocompleteContext):
    crystals = await db_get_available_crystal_types()
    return [c['name'] for c in crystals if ctx.value.lower() in c['name'].lower()][:25]

  @commands.slash_command(name="crystallize", description="Attach a crystal to a user's badge")
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
    "crystal_name",
    str,
    description="Crystal Name",
    required=True,
    autocomplete=autocomplete_crystal_name,
    max_length=128
  )
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
      color=discord.Color.green()
    )
    await ctx.respond(embed=embed, ephemeral=True)

