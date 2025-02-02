from common import *
from utils.check_channel_access import access_check

@bot.slash_command(
  name="trekduel",
  description="Return 2 random Trek Characters to fight to the death"
)
@commands.check(access_check)
async def trekduel(ctx:discord.ApplicationContext):
  """
  This function is the main entrypoint of the /trekduel command
  and will return a prompt with two random characters
  """
  f = open(config["commands"]["trekduel"]["data"])
  characters = f.read().splitlines()
  f.close()
  war_intros = ["War! Hoo! Good god y'all!", "War! We're going to war!", "That nonsense is *centuries* behind us!", "There's been no formal declaration, sir.", "Time to pluck a pigeon!"]
  pick_1 = random.choice(characters)
  pick_2 = random.choice(characters)
  chosen_intro = random.choice(war_intros)
  while pick_1 == pick_2:
    pick_2 = random.choice(characters)

  embed = discord.Embed(
    title=chosen_intro,
    description=f"Who would win in an arbitrary Star Trek duel?!",
    color=discord.Color.dark_gold()
  )
  embed.add_field(name="Red Corner", value=make_memory_alpha_link(pick_1))
  embed.add_field(name=" vs", value="⚔️")
  embed.add_field(name="Blue Corner", value=make_memory_alpha_link(pick_2))
  await ctx.respond(embed=embed)
  