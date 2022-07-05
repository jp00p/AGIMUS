from common import *

emojis = config["emojis"]

# @commands.check decorator function
# Can be injected in between @commands.check and your slash function to 
# restrict access to the "channels" from the command config by matching it with the function name
async def access_check(ctx):
  try:
    command_config = config["commands"][f"{ctx.command}"]
    has_channel_access = await perform_channel_check(ctx, command_config)
    if not has_channel_access:
      emojis = await ctx.guild.fetch_emojis()
      allowed_channels_list = command_config["channels"]
      if len(allowed_channels_list):
        allowed_channel_ids = get_channel_ids_list(allowed_channels_list)
        guild_channels = await ctx.guild.fetch_channels()
        allowed_channels = []
        for guild_channel in guild_channels:
          if guild_channel.id in allowed_channel_ids:
            allowed_channels.append(guild_channel.mention)

        allowed_embed = discord.Embed(
          title="Allowed Channels:",
          description="\n".join(allowed_channels)
        )
        allowed_embed.set_footer(
          text=f"Sorry! This command is not allowed in this channel.",
        )
        await ctx.respond(embed=allowed_embed, ephemeral=True)
      else:
        await ctx.respond(f"{emojis.get('guinan_beanflick_stance_threat')} Sorry! This command is not allowed in this channel.", ephemeral=True)
      
    return has_channel_access
  except BaseException as e:
    logger.info(e)

async def perform_channel_check(ctx, command_config):
  # Verify that we're allowed to execute the command in this channel
  allowed_channels = command_config.get("channels")
  blocked_channels = command_config.get("blocked_channels")

  # If we're in the development channel everything goes
  if ctx.channel.id == DEV_CHANNEL:
    logger.info(f"{Fore.LIGHTGREEN_EX}DEV CHANNEL COMMAND{Fore.RESET}")
    return True

  # logger.info(f"allowed channels: {allowed_channels}")

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
