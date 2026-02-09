from common import *
import discord

def _channel_ids_to_check(channel: discord.abc.GuildChannel) -> set[int]:
  # Return {channel_id, parent_id_if_thread}
  ids = {channel.id}
  parent_id = getattr(channel, 'parent_id', None)
  if parent_id:
    ids.add(parent_id)
  return ids

async def access_check(ctx):
  ctx_type = type(ctx).__name__
  try:
    command_config = config["commands"][f"{ctx.command}"]
    has_channel_access = await perform_channel_check(ctx, command_config)
    if not has_channel_access:
      allowed_channels_list = command_config["channels"]
      if len(allowed_channels_list):
        if ctx_type == 'ApplicationContext':
          allowed_channel_ids = get_channel_ids_list(allowed_channels_list)

          # Resolve mentions for both channels and threads if present
          allowed_channels = []
          for cid in allowed_channel_ids:
            # Try fast local getters first
            ch = ctx.guild.get_channel(cid) or ctx.bot.get_channel(cid)
            if ch is None:
              # Fallback to API (best effort)
              try:
                ch = await ctx.bot.fetch_channel(cid)
              except Exception:
                ch = None
            if ch is not None:
              allowed_channels.append(ch.mention)

          # Fallback: if nothing resolved, just show raw IDs
          if not allowed_channels:
            allowed_channels = [f"<#{cid}>" for cid in allowed_channel_ids]

          allowed_embed = discord.Embed(
            title="Not Allowed!",
            description=(
              "Sorry! This command is not allowed in this channel.\n\n"
              "**Allowed Channels (and their threads):**\n" + "\n".join(allowed_channels)
            ),
            color=discord.Color.red()
          )
          allowed_embed.set_image(url="https://i.imgur.com/QeUW4fV.gif")
          await ctx.respond(embed=allowed_embed, ephemeral=True)
      else:
        if ctx_type == 'ApplicationContext':
          allowed_embed = discord.Embed(
            title="Not Allowed!",
            description="Sorry! This command is not allowed in this channel.",
            color=discord.Color.red()
          )
          allowed_embed.set_image(url="https://i.imgur.com/QeUW4fV.gif")
          await ctx.respond(embed=allowed_embed, ephemeral=True)

    return has_channel_access
  except Exception as e:
    logger.info(f"Error in acess_check (probably forgot to add the command to configuration.json): {e}")
    return False

async def perform_channel_check(ctx, command_config):
  allowed_channels = command_config.get("channels")
  blocked_channels = command_config.get("blocked_channels")

  # Dev channel bypass
  if ctx.channel.id == DEV_CHANNEL:
    logger.info(f"{Fore.LIGHTGREEN_EX}* DEV CHANNEL COMMAND *{Fore.RESET}")
    return True

  current_ids = _channel_ids_to_check(ctx.channel)

  if allowed_channels:
    allowed_ids = set(get_channel_ids_list(allowed_channels))
    # Allowed if either the channel itself OR its parent (if thread) is listed
    is_allowed = bool(current_ids & allowed_ids)
    return is_allowed

  elif blocked_channels:
    blocked_ids = set(get_channel_ids_list(blocked_channels))
    # Blocked if either the channel or its parent is in the blocked list
    is_blocked = bool(current_ids & blocked_ids)
    return not is_blocked

  else:
    logger.info(f"{Fore.GREEN}Command authorized{Fore.RESET}")
    return True
