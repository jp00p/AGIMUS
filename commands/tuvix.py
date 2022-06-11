from .common import *

# tuvix() - Entrypoint for !tuvix command
# message[required]: discord.Message
# This function is the main entrypoint of the !tuvix command
# and will return a prompt with two random characters
async def tuvix(message:discord.Message):
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
  msg = message.author.mention + " -- a transporter accident has combined **"+pick_1+"** and **"+pick_2+"** into a Tuvix-like creature!  Do you sacrifice the two separate characters for this new one?  Do you give this abomination the Janeway treatment? Can you come up with a line of dialog for this character? Most importantly, do you name it:\n\n> **"+tuvix1+"** or **"+tuvix2+"**???"
  await message.channel.send(msg)
  