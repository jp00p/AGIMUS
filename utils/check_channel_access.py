from commands.common import *

emojis = config["emojis"]

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
  allowed_channels = command_config.get("channels")
  blocked_channels = command_config.get("blocked_channels")
  if allowed_channels is not None:
    if not (ctx.channel.id in allowed_channels):
      allowed_channel_names = []
      for id in allowed_channels:
        channel = client.get_channel(id)
        allowed_channel_names.append(channel.mention)
      await ctx.send(f"{emojis.get('guinan_beanflick_stance_threat')} Sorry! This command is not allowed in this channel. Allowed channels are: {', '.join(allowed_channel_names)}.", hidden=True)
      return False
    else:
      return True
  elif blocked_channels is not None:
    if (ctx.channel.id in blocked_channels):
      await ctx.send(f"{emojis.get('guinan_beanflick_stance_threat')} Sorry! This command is not allowed in this channel.", hidden=True)
      return False
    else:
      return True
  else:
    return True