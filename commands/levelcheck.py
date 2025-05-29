from common import *
from handlers.echelon_xp import get_xp_summary

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
