from calendar import c
from commands.common import *

async def check_channel_access(ctx, command_config):
  logger.info("Checking Channel Access")
  # Verify that we're allowed to perform drops in this channel
  allowed_channels = command_config["channels"]
  if not (ctx.channel.id in allowed_channels):
    allowed_channel_names = []
    for id in allowed_channels:
      channel = client.get_channel(id)
      allowed_channel_names.append(channel.mention)
    await ctx.send("<:ezri_frown_sad:757762138176749608> Sorry! Drops are not allowed in this channel. Allowed channels are: {}.".format(", ".join(allowed_channel_names)), hidden=True)
    return False
  else:
    return True