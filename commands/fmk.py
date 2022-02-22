from .common import *

# fmk() - Entrypoint for !fmk command
# message[required]: discord.Message
# This function is the main entrypoint of the !fmk command
# and will return a prompt with three random characters
async def fmk(message:discord.Message):
  f = open(config["commands"]["fmk"]["data"])
  fmk_characters = f.read().splitlines()
  f.close()
  choices = random.sample(fmk_characters, k=3)
  msg = message.author.mention + ": Fuck Marry Kill (or Kiss) -- \n**{}, {}, {}**".format(choices[0], choices[1], choices[2])
  await message.channel.send(msg)
  