from common import *
from handlers.xp import get_user_xp, get_xp_cap_progress, calculate_xp_for_next_level, get_total_xp_rank

@bot.slash_command(
  name="levelcheck",
  description="Display how close to your next level you are"
)
async def levelcheck(ctx:discord.ApplicationContext):
  user_xp_data = get_user_xp(ctx.author.id)
  current_xp = user_xp_data["xp"]
  current_level = user_xp_data["level"]

  previous_level_xp = calculate_xp_for_next_level(current_level - 1)
  base_xp = current_xp - previous_level_xp
  goal_xp = calculate_xp_for_next_level(current_level) - previous_level_xp

  # XP Cap Levels are Static to reach 420
  if current_level >= 176:
    # High Levelers - Static Level Up Progression per Every 420 XP
    cap_progress = get_xp_cap_progress(ctx.author.id)
    if cap_progress is not None:
      base_xp = cap_progress
      goal_xp = 420
  
  levelcheck_embed = discord.Embed(
    title="Level Up Progress:",
    description=f"Current level: {current_level} - {base_xp} out of {goal_xp} to {current_level + 1}.",
    color=discord.Color.random()
  )
  levelcheck_embed.add_field(
    name=f"Total XP",
    value=current_xp
  )
  levelcheck_embed.add_field(
    name=f"Rank",
    value=get_total_xp_rank(ctx.author.id)
  )

  await ctx.respond(
    embed=levelcheck_embed,
    ephemeral=True
  )
