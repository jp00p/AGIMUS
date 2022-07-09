from common import *
from utils.check_channel_access import access_check

# dustbuster() - Entrypoint for /dustbuster command
@bot.slash_command(
  name="dustbuster",
  description="Return 5 random Trek Characters as a possible Away Team"
)
@commands.check(access_check)
async def dustbuster(ctx:discord.ApplicationContext):
  f = open(config["commands"]["dustbuster"]["data"])
  characters = f.read().splitlines()
  f.close()

  crew_list = "\n\n"
  crew = random.sample(characters, k=5)
  for c in crew:
    crew_list += f"> {c} \n"
  embed = discord.Embed(
    title="Dustbuster Club",
    description="What kind of mission would this Dustbuster Club be suited for?",
    color=discord.Color.dark_gold()
  )
  embed.add_field(
    name="Away Team Members",
    value=crew_list
  )
  embed.set_footer(
    text="(Or are you totally screwed?)"
  )
  await ctx.respond(embed=embed)
  