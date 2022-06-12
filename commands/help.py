from .common import *

# help() - Entrypoint for !help command
# message[required]: discord.Message
# This function is the main entrypoint of the !help command
# and will display each help message in the channel that it was
# initiated, for the channel it was initiated.
async def help(message:discord.Message):
  f = open(config["commands"]["help"]["data"])
  help_data = json.load(f)
  f.close()
  for help_page in help_data:
    msg = "--------------------------------\n"
    if message.channel.id in help_page["channels"] and help_page["enabled"]:
      text_file = open(help_page["file"], "r")
      msg += text_file.read()
      text_file.close()
      await message.channel.send(msg)
      await asyncio.sleep(1)
