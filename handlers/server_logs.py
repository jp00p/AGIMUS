from common import *


# show_leave_message(member)
# shows a message when someone leaves the server
# member[required]: discord.Member
async def show_leave_message(member):
  if member.bot:
    return

  server_log_channel = bot.get_channel(SERVER_LOGS_CHANNEL)
  name = member.display_name
  msg = random.choice(config["leave_messages"]).format(name)
  msg += f" (Join date: {member.joined_at})"
  logger.info(f"{Fore.LIGHTRED_EX}{name} has left the server! :({Fore.RESET}")
  await server_log_channel.send(msg)

# show_nick_change_message(before,after)
# shows a message when someone changes their nickname on the server
# before[required]: discord.Member
# after[required]: discord.Member
async def show_nick_change_message(before,after):
  if before.bot or after.bot:
    return

  server_log_channel = bot.get_channel(SERVER_LOGS_CHANNEL)
  msg = f"**{before.display_name}** has changed their nickname to: **{after.display_name}**"
  logger.info(f"{Fore.LIGHTGREEN_EX}{before.display_name}{Fore.RESET} has changed their nickname to: {Fore.GREEN}{after.display_name}{Fore.RESET}")
  await server_log_channel.send(msg)

# show_channel_creation_message(channel)
# sends a message when someone creates a new channel on the server
# channel[required]: discord.Channel
async def show_channel_creation_message(channel):
  server_log_channel = bot.get_channel(SERVER_LOGS_CHANNEL)
  msg = f"✨ A new channel, **'#{channel.name}'**, was just created!"
  logger.info(f"{Fore.LIGHTGREEN_EX}#{channel.name}{Fore.RESET} was just created")
  await server_log_channel.send(msg)

# show_channel_deletion_message(channel)
# sends a message when someone deletes a channel on the server
# channel[required]: discord.Channel
async def show_channel_deletion_message(channel):
  server_log_channel = bot.get_channel(SERVER_LOGS_CHANNEL)
  msg = f"💥 **'#{channel.name}'**, was just deleted!"
  logger.info(f"{Fore.LIGHTGREEN_EX}#{channel.name}{Fore.RESET} was just deleted")
  await server_log_channel.send(msg)

# show_channel_rename_message(channel)
# sends a message when someone renames a channel on the server
# before[required]: discord.Channel
# after[required]: discord.Channel
async def show_channel_rename_message(before, after):
  if before.name == after.name:
    return

  server_log_channel = bot.get_channel(SERVER_LOGS_CHANNEL)
  msg = f"↪️ **'#{before.name}'** was renamed to **'#{after.name}'**!"
  logger.info(f"{Fore.LIGHTGREEN_EX}#{before.name}{Fore.RESET} was just renamed to {Fore.LIGHTGREEN_EX}#{after.name}{Fore.RESET}")
  await server_log_channel.send(msg)

# show_channel_topic_change_message(channel)
# sends a message when someone changes the topic of a channel on the server
# before[required]: discord.Channel
# after[required]: discord.Channel
async def show_channel_topic_change_message(before, after):
  if before.topic == after.topic:
    return

  server_log_channel = bot.get_channel(SERVER_LOGS_CHANNEL)
  msg = f"✏️ Topic in {after.mention} was updated to:\n\n> {after.topic}"
  logger.info(f"Topic in {Fore.LIGHTGREEN_EX}#{after.name}{Fore.RESET} updated")
  await server_log_channel.send(msg)