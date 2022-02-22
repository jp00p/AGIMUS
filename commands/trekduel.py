from .common import *

# trekduel() - Entrypoint for !trekduel command
# message[required]: discord.Message
# This function is the main entrypoint of the !trekduel command
# and will return a prompt with two random characters
async def trekduel(message:discord.Message):
  f = open(config["commands"]["trekduel"]["data"])
  characters = f.read().splitlines()
  f.close()
  war_intros = ["War! Hoo! Good god y'all!", "War! We're going to war!", "That nonsense is *centuries* behind us!", "There's been no formal declaration, sir.", "Time to pluck a pigeon!"]
  pick_1 = random.choice(characters)
  pick_2 = random.choice(characters)
  choose_intro = random.choice(war_intros)
  while pick_1 == pick_2:
    pick_2 = random.choice(characters)
  msg = choose_intro + "\n================\n" + message.author.mention + ": Who would win in an arbitrary Star Trek duel?!\n" + "\n> **"+pick_1+"** vs **"+pick_2+"**"
  await message.channel.send(msg)
  