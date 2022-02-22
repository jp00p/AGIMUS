from .common import *

# ping() - Entrypoint for !ping command
# message[required]: discord.Message
# This function is the main entrypoint of the !ping command
# and will return the client's latency value in milliseconds
async def ping(message:discord.Message):
  await message.channel.send("Pong! {}ms".format(round(client.latency * 1000)))
  