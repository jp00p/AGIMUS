from common import *
from utils.check_channel_access import access_check

@bot.slash_command(
  name="fmk",
  description="Return 3 random Trek Characters as an FMK prompt"
)
@commands.check(access_check)
async def fmk(ctx:discord.ApplicationContext):
  """
  This function is the main entrypoint of the /fmk command
  and will return a prompt with three random characters
  """
  f = open(config["commands"]["fmk"]["data"])
  fmk_characters = f.read().splitlines()
  f.close()

  choices = random.sample(fmk_characters, k=3)
  embed = discord.Embed(
    title="Fuck Marry Kill (or Kiss)",
    description="Who will it be?",
    color=discord.Color.dark_gold()
  )
  embed.add_field(
    name="Fuck",
    value=choices[0]
  )
  embed.add_field(
    name="Marry",
    value=choices[1]
  )
  embed.add_field(
    name="Kill (or Kiss)",
    value=choices[2]
  )
  await ctx.respond(embed=embed)