from common import *

@bot.slash_command(
  name="dice",
  description="Roll a d<sides>"
)
@option(
  name="sides",
  description="How many sides?",
  required=True,
  type=int
)
@option(
  name="Difficulty Class (Optional)",
  description="How high to succeed?",
  required=False,
  type=int
)
@option(
  name="Attribute Modifier (Optional)",
  description="Apply a modifier to the result to hit the DC? (DC is required)",
  required=False,
  type=int
)
async def dice(ctx:discord.ApplicationContext, sides:int, dc, modifier):
  if modifier and not dc:
    await ctx.respond(embed=discord.Embed(
      title=f"Difficulty Class is required if providing a modifier!",
      color=discord.Color.red(),
    ), ephemeral=True)
    return
  if sides:
    sides = int(sides)
    if sides <= 0:
      await ctx.respond(embed=discord.Embed(
        title=f"Sides must be a positive number!",
        color=discord.Color.red(),
      ), ephemeral=True)
      return
  if dc:
    dc = int(dc)
    if dc < 0:
      await ctx.respond(embed=discord.Embed(
        title=f"DC must be a positive number!",
        color=discord.Color.red(),
      ), ephemeral=True)
      return
  if modifier:
    modifier = int(modifier)

  description = "## Result: "
  result = random.randint(1, sides)
  if dc:
    final_result = result
    if modifier != 0:
      final_result = result + modifier
      description += f" **{final_result}** ({result} + ({modifier}))"
    else:
      description += f" **{final_result}**"

    if final_result > dc:
      description += f"\n\n**SUCCESS!**\n\n(Difficulty Class: {dc})"
    else:
      description += f"\n\n**FAIL!**\n\n(Difficulty Class: {dc})"

    if modifier:
      description += f"\n(Modifier: {modifier})"
  else:
    description += f" **{result}**"

  await ctx.respond(embed=discord.Embed(
    title=f"{ctx.author.display_name} rolled a **d{sides}!** 🎲",
    description=description,
    color=discord.Color.blurple()
  ))