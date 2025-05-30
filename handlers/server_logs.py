import pytz
from common import *


# show_leave_message(member)
# shows a message when someone leaves the server
# member[required]: discord.Member
async def show_leave_message(member:discord.Member):
  if member.bot:
    return

  server_logs_channel = bot.get_channel(get_channel_id(config["server_logs_channel"]))
  name = member.display_name

  pst_tz = pytz.timezone('America/Los_Angeles')
  raw_now = datetime.utcnow().replace(tzinfo=pytz.utc)
  aware_now = pst_tz.normalize(raw_now.astimezone(pst_tz))
  join_date = pst_tz.normalize(member.joined_at.astimezone(pst_tz)) # Member.joined_at is already UTC aware

  time_diff = aware_now - join_date
  total_days = time_diff.days
  total_seconds = time_diff.seconds

  years, remaining_days = divmod(total_days, 365)
  seconds = remaining_days * 24 * 3600 + total_seconds
  minutes, seconds = divmod(seconds, 60)
  hours, minutes = divmod(minutes, 60)
  days, hours = divmod(hours, 24)

  membership_length = ""
  if years >= 1:
    membership_length += f"{years} year{'s' if years > 1 else ''}, "
  membership_length += f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds"

  # Check if the user was banned
  guild = member.guild
  try:
    ban_entry = await guild.fetch_ban(member)
    if ban_entry:
      await show_banned_message(member, membership_length, join_date, ban_entry.reason)
      return
  except discord.NotFound:
    pass  # Member was not banned

  weather = random.choice(["gloomy", "rainy", "foggy", "chilly", "quiet", "soggy", "misty", "stormy"])

  embed = discord.Embed(
    title=random.choice(config["leave_messages"]).format(name) + " 😞",
    description=f"Profile: {member.mention}",
    color=discord.Color.random()
  )
  embed.add_field(
    name="Join Date",
    value=f"{join_date.strftime('%B %d, %Y')} (a {weather} {join_date.strftime('%A')})",
    inline=False
  )
  embed.add_field(
    name="Member For:",
    value=membership_length,
    inline=False
  )

  if member.avatar is not None:
    embed.set_author(
      name="",
      icon_url=member.avatar.url
    )

  logger.info(f"{Fore.LIGHTRED_EX}{name} has left the server! :({Fore.RESET}")

  await server_logs_channel.send(embed=embed)

async def show_banned_message(member:discord.Member, membership_length:str, reason:str, join_date):
  server_logs_channel = bot.get_channel(get_channel_id(config["server_logs_channel"]))

  embed = discord.Embed(
    title=f"🚨 {member.display_name} was BLOWN OUT AN AIRLOCK and BANNED! 🚨",
    description=f"Profile: {member.mention}",
    color=discord.Color.red()
  )
  embed.add_field(
    name="A PetaQ In The Midst For:",
    value=membership_length,
    inline=False
  )
  embed.add_field(
    name="Join Date",
    value=f"{join_date.strftime('%B %d, %Y')} (a {join_date.strftime('%A')}) that will live in infamy)",
    inline=False
  )
  embed.add_field(
    name="Reason:",
    value=reason,
    inline=False
  )
  if member.avatar is not None:
    embed.set_author(
      name="",
      icon_url=member.avatar.url
    )

  logger.info(f"{Fore.RED}{member.display_name} was banned from the server!{Fore.RESET}")

  await server_logs_channel.send(embed=embed)

# show_nick_change_message(before,after)
# shows a message when someone changes their nickname on the server
# before[required]: discord.Member
# after[required]: discord.Member
async def show_nick_change_message(before, after, scope = ""):
  if before.bot or after.bot:
    return

  if after.id in config["handlers"]["server_logs"]["nick_change_ignore_list"]:
    return

  # log the nickname change in the aliases table for use with /aliases
  async with AgimusDB() as query:
    sql = '''
      INSERT INTO user_aliases (user_discord_id, old_alias, new_alias)
        VALUES (%s, %s, %s)
    '''
    vals = (f"{after.id}", before.display_name, after.display_name)
    await query.execute(sql, vals)

  logger.info(f"{Fore.LIGHTGREEN_EX}{before.display_name}{Fore.RESET} has changed their {scope} nickname to: {Fore.GREEN}{after.display_name}{Fore.RESET}")
  embed = discord.Embed(
    title=f"'{before.display_name}' has changed their {scope} nickname!",
    description=f"Profile: {after.mention}",
    color=discord.Color.random()
  )
  embed.add_field(
    name="Previous Nickname",
    value=before.display_name,
    inline=False
  )
  embed.add_field(
    name="New Nickname",
    value=after.display_name,
    inline=False
  )

  if after.avatar is not None:
    embed.set_author(
      name="",
      icon_url=after.avatar.url
    )

  server_logs_channel = bot.get_channel(get_channel_id(config["server_logs_channel"]))
  await server_logs_channel.send(embed=embed)

# show_channel_creation_message(channel)
# sends a message when someone creates a new channel on the server
async def show_channel_creation_message(channel):
  server_logs_channel = bot.get_channel(get_channel_id(config["server_logs_channel"]))
  msg = f"✨ A new channel, **'#{channel.name}'**, was just created!"
  logger.info(f"{Fore.LIGHTGREEN_EX}#{channel.name}{Fore.RESET} was just created")
  await server_logs_channel.send(msg)

# show_channel_deletion_message(channel)
# sends a message when someone deletes a channel on the server
async def show_channel_deletion_message(channel):
  server_logs_channel = bot.get_channel(get_channel_id(config["server_logs_channel"]))
  msg = f"💥 **'#{channel.name}'**, was just deleted!"
  logger.info(f"{Fore.LIGHTGREEN_EX}#{channel.name}{Fore.RESET} was just deleted")
  await server_logs_channel.send(msg)

# show_channel_rename_message(channel)
# sends a message when someone renames a channel on the server
# before[required]: discord channel
# after[required]: discord channel
async def show_channel_rename_message(before, after):
  if before.name == after.name:
    return

  server_logs_channel = bot.get_channel(get_channel_id(config["server_logs_channel"]))
  msg = f"↪️ **'#{before.name}'** was renamed to **'#{after.name}'**!"
  logger.info(f"{Fore.LIGHTGREEN_EX}#{before.name}{Fore.RESET} was just renamed to {Fore.LIGHTGREEN_EX}#{after.name}{Fore.RESET}")
  await server_logs_channel.send(msg)

# show_channel_topic_change_message(channel)
# sends a message when someone changes the topic of a channel on the server
# before[required]: discord channel
# after[required]: discord channel
async def show_channel_topic_change_message(before, after):
  if before.topic == after.topic:
    return

  server_logs_channel = bot.get_channel(get_channel_id(config["server_logs_channel"]))
  msg = f"✏️ Topic in {after.mention} was updated to:\n\n> {after.topic}"
  logger.info(f"Topic in {Fore.LIGHTGREEN_EX}#{after.name}{Fore.RESET} updated")
  await server_logs_channel.send(msg)