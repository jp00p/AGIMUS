from commands.common import *

emojis = config["emojis"]

# @slash_check_channel_access decorator
# Can be injected in between @slash.slash and your slash function to 
# restrict access to the "channels" from the command config
def slash_check_channel_access(command_config):
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
        await ctx.send(f"{emojis.get('guinan_beanflick_stance_threat')} Sorry! This command is not allowed in this channel.", hidden=True)
        return
    return decorator
  return container

async def perform_channel_check(ctx, command_config):
  # Verify that we're allowed to execute the command in this channel
  allowed_channels = command_config.get("channels")
  blocked_channels = command_config.get("blocked_channels")

  # If we're in the development channel everything goes
  if ctx.channel.id == DEV_CHANNEL:
    logger.info(f"{Fore.LIGHTGREEN_EX}DEV COMMAND{Fore.RESET}")
    return True

  # Otherwise check allowed/blocked channel lists
  if allowed_channels:
    allowed_channel_ids = get_channel_ids_list(allowed_channels)
    is_allowed = ctx.channel.id in allowed_channel_ids
    logger.info(f"Allowed in this channel? {Fore.CYAN}{is_allowed}{Fore.RESET}")
    return ctx.channel.id in allowed_channel_ids
  elif blocked_channels:
    blocked_channel_ids = get_channel_ids_list(blocked_channels)
    is_not_blocked = ctx.channel.id not in blocked_channel_ids
    logger.info(f"Not blocked in this channel? {Fore.CYAN}{is_not_blocked}{Fore.RESET}")
    return ctx.channel.id not in blocked_channel_ids
  else:
    return True
