from .common import *

# dustbuster() - Entrypoint for !dustbuster command
# message[required]: discord.Message
# This function is the main entrypoint of the !dustbuster command
# and will return a prompt with two random characters
async def dustbuster(message:discord.Message):
  f = open(config["commands"]["dustbuster"]["data"])
  characters = f.read().splitlines()
  f.close()
  crew = []
  msg = message.author.mention + ", what kind of mission would this Dustbuster club be suited for?  Or are you totally screwed?\n"
  crew = random.sample(characters, k=5)
  for c in crew:
    msg += "> **"+ c + "**\n"
  await message.channel.send(msg)
  