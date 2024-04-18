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
  required=True,
  type=int
)
@option(
  name="Attribute Modifier (Optional)",
  description="Apply a modifier to the result to hit the DC? (DC is required)",
  required=True,
  type=int
)
async def dice(ctx:discord.ApplicationContext, sides:int, dc:int, modifier:int):
  if isinstance(modifier, int) and not isinstance(dc, int):
    await ctx.respond(embed=discord.Embed(
      title=f"Difficulty Class is required if providing a modifier!",
      color=discord.Color.red()
    ))
    return

  result = random.randint(1, sides)
  description = f"## Result:\n**{result}**"
  if isinstance(dc, int):
    if isinstance(modifier, int):
      result = result + modifier
    if result > dc:
      description += f"\n\n**SUCCESS!**\n\n(Difficulty Class: {dc})"
    if isinstance(modifier, int):
      description += f"\n(Modifier: {modifier})"

  await ctx.respond(embed=discord.Embed(
    title=f"{ctx.author.mention} rolled a **d{sides}!**",
    description=description,
    color=discord.Color.blurple()
  ))