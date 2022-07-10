from common import *
from utils.check_channel_access import access_check

# trektalk() - Entrypoint for /trektalk command
# This function is the main entrypoint of the /trektalk command
# and will a trek related prompt
@bot.slash_command(
  name="trektalk",
  description="Return a random Trek Discussion Prompt"
)
@commands.check(access_check)
async def trektalk(ctx:discord.ApplicationContext):
  f = open(config["commands"]["trektalk"]["data"])
  prompts = f.read().splitlines()
  f.close()
  pick = random.choice(prompts)
  await ctx.respond(embed=discord.Embed(
    title="Let's Talk Trek!",
    description=f"Please answer or talk about the following prompt!\nOne word answers are highly discouraged!\n\n> **{pick}**",
    color=discord.Color.dark_gold()
  ))
  