from common import *

async def handle_reply_restricted(message:discord.Message):
  blocked_channels = get_channel_ids_list(config["handlers"]["reply_restricted"]["blocked_channels"])
  if message.channel.id not in blocked_channels:
    return

  if message.reference or message.mentions:
    try:
      notify_embed = discord.Embed(
        title=f"Whoops, replies restricted.",
        description=f"Sorry, your message has been removed. We don't allow replies/feedback in {message.channel.mention}, it's just intended as space to simply post messages without feedback.\n\nPlease see the channel description! Thanks.",
        color=discord.Color.red()
      )
      notify_embed.set_footer(text="S'all good, no worries. This is an automated message, if you have questions please ask a moderator!")
      await message.author.send(embed=notify_embed)
    except discord.Forbidden as e:
      logger.info(f"Unable to send Cornmander stripping message to {message.author.display_name}, they have their DMs closed.")
      pass
    await message.delete()