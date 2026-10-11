from common import *
from handlers.echelon_xp import get_xp_summary

from queries.badge_info import db_get_all_badge_info
from queries.badge_instances import db_get_badge_instances_prestige_counts_for_user
from queries.crystal_instances import db_get_user_crystal_buffer_count
from queries.tongo import db_get_tongo_dividends
from utils.prestige import PRESTIGE_TIERS

@bot.slash_command(
  name="levelcheck",
  description="Display how close you are to your next Echelon Level"
)
async def levelcheck(ctx: discord.ApplicationContext):
  await ctx.defer(ephemeral=True)

  xp_data = await get_xp_summary(ctx.author.id)

  level = xp_data['level']
  xp_into_level = xp_data['xp_into_level']
  xp_required = xp_data['xp_required']
  total_xp = xp_data['total_xp']
  badge_tier_counts = await db_get_badge_instances_prestige_counts_for_user(ctx.author.id)
  all_badges = await db_get_all_badge_info()
  available_badge_count = len([
    badge
    for badge in all_badges
    if not badge['special']
  ])

  embed = discord.Embed(
    title="📈 Echelon XP Progress",
    color=discord.Color.teal()
  )
  embed.add_field(
    name="Current Echelon",
    value=f"Level **{level}**",
    inline=False
  )
  embed.add_field(
    name="Progress to Next Level",
    value=f"{xp_into_level:,} / {xp_required:,} XP",
    inline=False
  )
  embed.add_field(
    name="Total XP Earned",
    value=f"{total_xp:,} XP",
    inline=False
  )

  if badge_tier_counts:
    badge_tier_lines = [
      f"* **{PRESTIGE_TIERS[row['prestige_level']]}:** {row['count']:,} / {available_badge_count:,} Badges"
      for row in badge_tier_counts
    ]
    embed.add_field(
      name="Badges by Prestige Tier",
      value="\n".join(badge_tier_lines),
      inline=False
    )

  embed.set_footer(text="Type '/profile' for all your deets.")

  await ctx.respond(embed=embed)

@bot.slash_command(
  name="currencies",
  description="Display how many of the various AGIMUS Credits you possess"
)
async def currencies(ctx: discord.ApplicationContext):
  await ctx.defer(ephemeral=True)
  user_id = ctx.author.id

  crystal_pattern_buffers = await db_get_user_crystal_buffer_count(user_id)
  record = await db_get_tongo_dividends(user_id)
  tongo_dividends = record['current_balance'] if record else 0
  user_data = await get_user(user_id)
  recreational_credits = user_data['score']

  embed = discord.Embed(
    title=f"{get_emoji('agimus')} AGIMUS Credits",
    color=discord.Color.teal()
  )
  embed.add_field(
    name="Crystal Pattern Buffers",
    value=f"**{crystal_pattern_buffers:,}** Patterns",
    inline=False
  )
  embed.add_field(
    name="Tongo Dividends",
    value=f"**{tongo_dividends:,}** Dividends",
    inline=False
  )
  embed.add_field(
    name="Shop Credits (Bot Games Score)",
    value=f"**{recreational_credits:,}** Credits",
    inline=False
  )
  embed.set_footer(text="Type '/profile' for other deets.")

  await ctx.respond(embed=embed)
