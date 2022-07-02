from .common import *

# qget() - Entrypoint for !qget command
# message[required]: discord.Message
# This function is the main entrypoint of the !qget command
# and will get a user's 
async def qget(message:discord.Message):
  logger.debug("!qget")
  selected_user = message.content.lower().replace("!qget ", "").replace("<@", "").replace(">","")
  logger.info(f"{Fore.LIGHTGREEN_EX}!qget selected_user: {Style.BRIGHT}{selected_user}{Style.RESET_ALL}{Fore.RESET}")
  if is_integer(selected_user):
    await display_user(selected_user, message)
  else:
    await message.channel.send("Usage: !qget [user]")


# qset() - Entrypoint for !qset command
# message[required]: discord.Message
# This function is the main entrypoint of the !qset command
# and will get a user's 
async def qset(message:discord.Message):
  f = open(config["commands"]["qget"]["data"])
  user_columns = json.load(f)
  f.close()
  logger.debug("!qset")
  qspl = message.content.lower().replace("!qset ", "").split()
  selected_user = qspl[0].replace("<@", "").replace(">","")
  change_column = qspl[1]
  change_value  = qspl[2]
  logger.info(f"!get selected_user: {selected_user}")
  this_user = get_user(selected_user)
  logger.debug(f"this_user: {this_user}")
  modifiable_ints = ["score", "spins", "jackpots", "wager", "high_roller", "chips", "xp"]
  modifiable_strings = ["profile_card", "profile_badge"]
  if change_column not in modifiable_ints and change_column not in modifiable_strings:
    logger.error(f"{change_column} not in {modifiable_strings} or {modifiable_ints}")
    await message.channel.send("Can only modify these values:```"+tabulate(modifiable_ints, headers="firstrow")+"``````"+tabulate(modifiable_strings, headers="firstrow")+"```")
  else:
    logger.info(f"Modifying: {change_column}")
    if change_column in modifiable_ints:
      logger.info(f"{change_column} in {modifiable_ints}")
      if is_integer(change_value):
        logger.info(f"{change_value} not int")
      logger.info(f"send update_user({selected_user}, {change_column}, {change_value})")
      update_user(selected_user, change_column, change_value)
    elif change_column in modifiable_strings:
      logger.info(f"{change_column} in {modifiable_strings}")
      update_user(selected_user, change_column, change_value)
    await display_user(selected_user, message)


async def display_user(user_id:discord.User, message:discord.Message):
  f = open(config["commands"]["qget"]["data"])
  user_columns = json.load(f)
  f.close()
  user_data = get_user(user_id)
  logger.debug(f"this_user: {user_data}")

  user = await client.fetch_user(user_id)
  embed = discord.Embed()
  embed.set_author(
    name=user.display_name,
    icon_url=user.avatar_url
  )
  for header in user_columns["display_headers"]:
    embed.add_field(
      name=header,
      value=user_data[header]
    )
  member_info = await message.guild.fetch_member(user_id)
  embed.set_footer(text=f"User Joined: {member_info.joined_at.strftime('%A, %b %-d %Y - %I:%M %p')}; Top Role: {member_info.top_role.name}")
  await message.channel.send(embed=embed)