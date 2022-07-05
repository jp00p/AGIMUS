from common import *
from utils.check_channel_access import access_check

# tuvix() - Entrypoint for !tuvix command
# This function is the main entrypoint of the !tuvix command
# and will return a prompt with two random characters
@bot.slash_command(
  name="tuvix",
  description="Return two Trek characters to be Tuvix'd as a discussion prompt!"
)
@commands.check(access_check)
async def tuvix(ctx:discord.ApplicationContext):
  f = open(config["commands"]["tuvix"]["data"])
  tuvixes = f.read().splitlines()
  f.close()
  pick_1 = random.choice(tuvixes)
  pick_2 = random.choice(tuvixes)
  while pick_1 == pick_2:
    pick_2 = random.choice(tuvixes)
  name1 = [pick_1[:len(pick_1)//2], pick_1[len(pick_1)//2:]]
  name2 = [pick_2[:len(pick_2)//2], pick_2[len(pick_2)//2:]]
  tuvix1 = str(name1[0]+name2[1]).replace(" ", "").title().strip()
  tuvix2 = str(name2[0]+name1[1]).replace(" ", "").title().strip()
  # msg = message.author.mention + " -- a transporter accident has combined **"+pick_1+"** and **"+pick_2+"** into a Tuvix-like creature!  Do you sacrifice the two separate characters for this new one?  Do you give this abomination the Janeway treatment? Can you come up with a line of dialog for this character? Most importantly, do you name it:\n\n> **"+tuvix1+"** or **"+tuvix2+"**???"
  # await message.channel.send(msg)

  embed = discord.Embed(
    title=f"A terrible transporter accident occurred! 💥",
    description=f"**{pick_1}** and **{pick_2}** have been combined into a Tuvix-like Creature!\n\nDo you sacrifice the two separate characters for this new one?\nDo you give this abomination the Janeway treatment?\nCan you come up with a line of dialog for this character?\n\n*Most importantly*, do you name it:\n",
    color=discord.Color.dark_gold()
  )
  embed.add_field(name="Choice A", value=tuvix1)
  embed.add_field(name="🧬", value="or")
  embed.add_field(name="Choice B", value=tuvix2)
  await ctx.respond(embed=embed)
  