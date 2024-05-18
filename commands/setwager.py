from common import *


wager_choices = [1, 5, 10, 25, 50, 100]

@bot.slash_command(
  name="setwager",
  description="Set your default wager for /poker and /slots"
)
@option(
  name="wager",
  description="How much would you like to wager?",
  required=True,
  choices=[
    discord.OptionChoice(
      name=str(i),
      value=i
    )
    for i in wager_choices
  ]
)
async def setwager(ctx:discord.ApplicationContext, wager:int):
  """
  This function is the main entrypoint of the /setwager command
  and will set a user's wager value to the amount passed
  """
  player = await get_user(ctx.author.id)
  current_wager = player["wager"]
  if wager in wager_choices:
    await db_set_player_wager(ctx.author.id, wager)
    await ctx.respond(embed=discord.Embed(
      title="Wager Updated!",
      description=f"{ctx.author.mention}: Your default wager has been changed from `{current_wager}` to `{wager}`",
      color=discord.Color.green()
    ), ephemeral=True)
  else:
    await ctx.respond(embed=discord.Embed(
      title="Invalid Wager",
      description=f"{ctx.author.mention}: Wager must be from the options provided ({', '.join(wager_choices)}).\nYour current wager is: `{current_wager}`",
      color=discord.Color.red()
    ), ephemeral=True)


async def db_set_player_wager(discord_id, amt):
  """
  This function takes a player's discord ID
  and a positive integer and updates the wager
  value for that user in the db
  """
  async with AgimusDB(dictionary=True) as query:
    amt = max(amt, 0)
    sql = "UPDATE users SET wager = %s WHERE discord_id = %s"
    vals = (amt, discord_id)
    await query.execute(sql, vals)
