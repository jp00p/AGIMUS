from .common import *

# report() - Entrypoint for !report command
# message[required]: discord.Message
# This function is the main entrypoint of the !report command
async def report(message:discord.Message):
  global LOG
  if len(LOG) != 0:
    msg = "```QUIZ REPORT: \n"
    for l in LOG:
      msg += "{0} ({1}:{2})\n".format(l[0], l[1], l[2])
    msg += "```"
  else:
    msg = "No log entries currently"
  await message.channel.send(msg)
  