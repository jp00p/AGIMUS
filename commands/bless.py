from common import *

command_config = config["commands"]["bless"]

# Load JSON Data
f = open(command_config["data"])
curse_data = json.load(f)
f.close()

@bot.slash_command(
  name="bless",
  description="Small Blessings for a Balanced Heart (apers' Bless Service)"
)
async def bless(ctx:discord.ApplicationContext):
  selected_blessing = random.choice(curse_data['blessings'])
  embed = discord.Embed(
    description=f"> {selected_blessing}",
    color=discord.Color.magenta()
  )
  await ctx.respond(embed=embed)
