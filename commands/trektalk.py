from .common import *

# trektalk() - Entrypoint for !trektalk command
# message[required]: discord.Message
# This function is the main entrypoint of the !trektalk command
# and will a trek related prompt
async def trektalk(message:discord.Message):
  f = open(config["commands"]["trektalk"]["data"])
  prompts = f.read().splitlines()
  f.close()
  pick = random.choice(prompts)
  msg =  message.author.mention + "! You want to talk about Trek? Let's talk about Trek! \nPlease answer or talk about the following prompt! One word answers are highly discouraged!\n > **"+pick+"**"
  await message.channel.send(msg)
  