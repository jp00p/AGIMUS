from commands.common import *

# @check_channel_access decorator
# Can be injected in between @slash.slash and your slash function to 
# restrict access to the "channels" from the command config
def check_channel_access(command_config):
  # Container accepts the actual drop function as `command`
  def container(command):
    # The decorator is what actually performs the check before determining whether to execute the command
    async def decorator(*dargs, **dkwargs):
      # First argument sent to the decorator is the Slash Context we need for the channel check
      ctx = dargs[0]
      has_channel_access = await perform_channel_check(ctx, command_config)
      if (has_channel_access):
        # If we have access, go ahead and execute the command and pass through the arguments sent to the decorator
        await command(*dargs, **dkwargs)
      else:
        # No-Op
        return
    return decorator
  return container

async def perform_channel_check(ctx, command_config):
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