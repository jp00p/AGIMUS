from .common import *

# categories() - Entrypoint for !categories command
# message[required]: discord.Message
# This function is the main entrypoint of the !categories command
# and will display the possible trivia categories
async def categories(message:discord.Message):
  f = open(config["commands"]["categories"]["data"])
  trivia_data = json.load(f)
  f.close()
  msg = "Trivia Categories:\n"
  for c in range(len(trivia_data["categories"])):
    msg += "`{}`. {}\n".format(c+1, trivia_data["categories"][c])
  example = random.randint(0,len(config["commands"]["categories"]["data"]))
  msg += "\n example: Type `!trivia {}` to play the {} category".format(example+1, trivia_data["categories"][example])
  await message.channel.send(msg)