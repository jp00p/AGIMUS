from common import *
from handlers.echelon_xp import get_xp_summary

from queries.crystal_instances import db_get_user_crystal_buffer_count
from queries.tongo import db_get_tongo_dividends

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
  embed.set_footer(text="Type '/profile' for all your deets.")

  await ctx.respond(embed=embed)

@bot.slash_command(
  name="currencies",
  description="Display how many of the various AGIMUS Credits you possess (Pattern Buffers, Dividends, Shop Credits)"
)
async def currencies(ctx: discord.ApplicationContext):
  await ctx.defer(ephemeral=True)
  user_id = ctx.author.id

  crystal_pattern_buffers = await db_get_user_crystal_buffer_count(user_id)
  record = await db_get_tongo_dividends(user_id)
  tongo_dividends = record['current_balance'] if record else 0
  user_data = get_user(user_id)
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
    value=f"{tongo_dividends:,} Dividends",
    inline=False
  )
  embed.add_field(
    name="Shop Credits (Bot Games Score)",
    value=f"{recreational_credits:,} Credits",
    inline=False
  )
  embed.set_footer(text="Type '/profile' for other deets.")

  await ctx.respond(embed=embed)
