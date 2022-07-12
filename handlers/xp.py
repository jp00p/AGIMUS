import math
from time import sleep
from numpy import block
from common import *
from commands.badges import give_user_badge, send_badge_reward_message

# rainbow of colors to cycle through for the logs
xp_colors = [
    Fore.RED,
    Fore.LIGHTRED_EX,
    Fore.YELLOW,
    Fore.LIGHTYELLOW_EX,
    Fore.GREEN,
    Fore.LIGHTGREEN_EX,
    Fore.LIGHTCYAN_EX,
    Fore.CYAN,
    Fore.LIGHTBLUE_EX,
    Fore.BLUE, 
    Fore.MAGENTA,
    Fore.LIGHTMAGENTA_EX
]
current_color = 0
blocked_channel_ids = get_channel_ids_list(config["handlers"]["xp"]["blocked_channels"])
notification_channel_id = get_channel_id(config["handlers"]["xp"]["notification_channel"])

reasons = {
  "posted_message" : "posting a message",
  "added_reaction" : "adding a reaction",
  "got_reactions"  : "getting lots of reactions"

}

# handle_message_xp(message) - calculates xp for a given message
# message[required]: discord.Message
async def handle_message_xp(message:discord.Message):   
    # we don't like bots round here, or some channels
    if message.author.bot or message.channel.id in blocked_channel_ids:
      return

    # base XP
    xp_amt = 0

    # if the message is equal to or longer than 3 words +1 xp
    if len(message.content.split()) >= 3:
      xp_amt += 1
      
      # if that message also has any of our server emoji, +1 xp
      # case sensitive (cool != COOL)
      for e in config["all_emoji"]:
        if message.content.find(e) != -1:
          xp_amt += 1
          break

    # if the message is longer than 33 words +1 more xp
    if len(message.content.split()) > 33:
      xp_amt += 1

    # ...and 66, +1 more xp
    if len(message.content.split()) > 66:
      xp_amt += 1

    # if there's an attachment, +1 xp
    if len(message.attachments) > 0:
      xp_amt += 1 

    if xp_amt != 0:
      await increment_user_xp(message.author, xp_amt, "posted_message", message.channel) # commit the xp gain to the db

    # Handle Auto-Promotions
    promotion_roles_config = config["roles"]["promotion_roles"]
    if promotion_roles_config["enabled"]:
      cadet_role = promotion_roles_config["ranks"]["cadet"]
      ensign_role = promotion_roles_config["ranks"]["ensign"]
      guild_roles = await message.author.guild.fetch_roles()
      guild_role_names = [r.name for r in guild_roles]
      if cadet_role in guild_role_names and ensign_role in guild_role_names:
        await handle_intro_channel_promotion(message)
        await handle_rank_xp_promotion(message, xp_amt)
      else:
        logger.info(f"Promotion is enabled but {Fore.CYAN}Cadet{Fore.RESET} and {Fore.CYAN}Ensign{Fore.RESET} roles are not available from the guild!")
        logger.info(f"Available roles are: {Style.BRIGHT}{guild_role_names}{Style.RESET_ALL}.")


# If this message is in the intro channel, handle their auto-promotion
async def handle_intro_channel_promotion(message):
  promotion_roles_config = config["roles"]["promotion_roles"]

  if message.channel.id == INTRO_CHANNEL:
    member = message.author
    cadet_role_name = promotion_roles_config["ranks"]["cadet"]
    author_role_names = [r.name for r in message.author.roles]
    guild_roles = await message.author.guild.fetch_roles()

    cadet_role = None
    for role in guild_roles:
      if role.name == cadet_role_name:
        cadet_role = role

    if cadet_role_name not in author_role_names:
      # if they don't have this role, give them this role!
      logger.info(f"Adding {Fore.CYAN}Cadet{Fore.RESET} role to {Style.BRIGHT}{message.author.name}{Style.RESET_ALL}")
      await member.add_roles(cadet_role)
        
      # add reactions to the message they posted
      welcome_reacts = [get_emoji("ben_wave"), get_emoji("adam_wave")]
      random.shuffle(welcome_reacts)
      for i in welcome_reacts:
        logger.info(f"{Fore.LIGHTBLACK_EX}Adding react {i} to intro message{Fore.RESET}")
        await message.add_reaction(i)

# If they've hit an XP threshold, auto-promote to general ranks
async def handle_rank_xp_promotion(message, xp):
  promotion_roles_config = config["roles"]["promotion_roles"]

  cadet_role_name = config["roles"]["promotion_roles"]["ranks"]["cadet"]
  ensign_role_name = config["roles"]["promotion_roles"]["ranks"]["ensign"]
  author_role_names = [r.name for r in message.author.roles]

  guild_roles = await message.author.guild.fetch_roles()

  cadet_role = None
  ensign_role = None
  for role in guild_roles:
    if role.name == cadet_role_name:
      cadet_role = role
    if role.name == ensign_role_name:
      ensign_role = role

  user_xp = get_user_xp(message.author.id).get("xp") # second element of tuple is the xp

  if cadet_role_name not in author_role_names:
    # if they don't have cadet yet and they are over the required xp, give it to them
    if user_xp >= promotion_roles_config["required_rank_xp"]["cadet"]:
      await message.author.add_roles(cadet_role)
      logger.info(f"{Style.BRIGHT}{message.author.display_name}{Style.RESET_ALL} has been promoted to {Fore.CYAN}Cadet{Fore.RESET} via XP!")
  elif ensign_role_name not in author_role_names:
    # if they do have cadet but not ensign yet, give it to them
    if user_xp >= promotion_roles_config["required_rank_xp"]["ensign"]:
      await message.author.add_roles(ensign_role)
      logger.info(f"{Style.BRIGHT}{message.author.display_name}{Style.RESET_ALL} has been promoted to {Fore.GREEN}Ensign{Fore.RESET} via XP!")


@bot.slash_command(
  name="disable_xp",
  description="Disable XP and stop receiving notifications from the bot"
)
@option(
  name="disable",
  description="Disable the notifications and stop participating in the XP game?",
  required=True,
  choices=[
    discord.OptionChoice(
      name="No",
      value="no"
    ),
    discord.OptionChoice(
      name="Yes",
      value="yes"
    )
  ]
)
async def disable_xp(ctx:discord.ApplicationContext, disable:str):
  user_selection = (disable == "yes")
  db = getDB()
  query = db.cursor()
  sql = "UPDATE users SET xp_enabled = %s WHERE discord_id = %s"
  vals = (not user_selection, ctx.user.id,)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()
  response_msg = ""
  if user_selection:
    response_msg = "XP logging and notifications have been disabled for you!"
    logger.info(f"{ctx.user.display_name} has disabled xp")
  else:
    response_msg = "XP logging and notifications have been re-enabled for you!"
  await ctx.respond(response_msg, ephemeral=True)


async def handle_react_xp(reaction:discord.Reaction, user:discord.User):
  # Check if this user has already reacted to this message with this emoji

  if reaction.message.author.bot or user.bot or reaction.message.channel.id in blocked_channel_ids:
    return

  global current_color

  reaction_already_counted = check_react_history(reaction, user)
  if reaction_already_counted:
    return
  
  log_react_history(reaction, user)
  await increment_user_xp(user, 1, "added_reaction", reaction.message.channel)

  # Give the author some bonus XP if they've made a particularly reaction-worthy message!
  threshold_relevant_emojis = [
    get_emoji("data_lmao_lol"),
    get_emoji("picard_yes_happy_celebrate"),
    get_emoji("tgg_love_heart"),
    get_emoji("bits"),
    get_emoji("weyoun_love_heart"),
    get_emoji("tendi_smile_happy"),
    get_emoji("THIS"),
    get_emoji("NICE"),
    get_emoji("YES"),
    get_emoji("picard_yes_happy_celebrate")
  ]

  xp_amt = 0
  if reaction.emoji in threshold_relevant_emojis and reaction.count >= 5 and reaction.count < 10:
    xp_amt = 1
  
  if f"{reaction.emoji}" in threshold_relevant_emojis and reaction.count >= 10 and reaction.count < 20:
    xp_amt = 2

  if f"{reaction.emoji}" in threshold_relevant_emojis and reaction.count >= 20:
    xp_amt = 5

  if xp_amt > 0:
    await increment_user_xp(reaction.message.author, xp_amt, "got_reactions", reaction.message.channel) 

# calculate_xp_for_next_level(current_level)
# current_level[required]: int
# returns the amount of xp required to level up for the given level
def calculate_xp_for_next_level(current_level:int):
  return int( (current_level*69) + (current_level * current_level) - 1)

# util function for debug - shows an XP chart like D&D
def show_list_of_levels():
  level_chart = ""
  previous_xp_amt = 0
  for i in range(101):
    xp_required = calculate_xp_for_next_level(i)
    amt_diff = xp_required - previous_xp_amt
    previous_xp_amt = xp_required
    level_chart += f"{i} - {xp_required} - ({amt_diff})\n"
  logger.info(level_chart)

# level_up_user(user, level)
# user[required]:discord.User
# level[required]:int
# level up user to next level and give them a badge (in the DB)
# also fires the send_level_up_message function
async def level_up_user(user:discord.User, level:int):
  rainbow_l = f"{Back.RESET}{Back.RED} {Back.YELLOW} {Back.GREEN} {Back.CYAN} {Back.BLUE} {Back.MAGENTA} {Back.RESET}"
  rainbow_r = f"{Back.RESET}{Back.MAGENTA} {Back.BLUE} {Back.CYAN} {Back.GREEN} {Back.YELLOW} {Back.RED} {Back.RESET}"
  logger.info(f"{rainbow_l} {Style.BRIGHT}{user.display_name}{Style.RESET_ALL} has reached {Style.BRIGHT}level {level}!{Style.RESET_ALL} {rainbow_r}")
  db = getDB()
  query = db.cursor()
  sql = "UPDATE users SET level = level + 1 WHERE discord_id = %s"
  vals = (user.id,)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()
  badge = give_user_badge(user.id)
  await send_level_up_message(user, level, badge)

# send_level_up_message(user, level, badge)
# user[required]:discord.User
# level[required]:int
# badge[required]:str
async def send_level_up_message(user:discord.User, level:int, badge:str):
  channel = bot.get_channel(notification_channel_id)
  embed_title = "Level up!"
  thumbnail_image = random.choice(config["handlers"]["xp"]["celebration_images"])
  embed_description = f"{user.mention} has reached **level {level}** and earned a new badge!"
  message = f"{user.mention} - Level up! See all your badges by typing `/badges` - disable this by typing `/disable_xp`"
  await send_badge_reward_message(message, embed_description, embed_title, channel, thumbnail_image, badge, user)

# increment_user_xp(author, amt)
# messauge.author[required]: discord.User
# amt[required]: int
# channel[required]: discord.Channel
# This function will increment a users' XP and log the gain to the history
async def increment_user_xp(user, amt, reason, channel):
  global current_color
  msg_color = xp_colors[current_color]
  star = f"{msg_color}{Style.BRIGHT}*{Style.NORMAL}{Fore.RESET}"
  db = getDB()
  query = db.cursor()
  sql = "UPDATE users SET xp = xp + %s, name = %s WHERE discord_id = %s AND xp_enabled = 1"
  vals = (amt, user.display_name, user.id)
  query.execute(sql, vals)
  updated = query.rowcount
  db.commit()
  query.close()
  db.close()
  if updated > 0:
    log_xp_history(user.id, amt, channel.id, reason)
    # If reaction hasn't been logged already, go ahead and do so and then award some XP!
    reason_text = reasons[reason]
    if not reason_text:
      reason_text = reason
    logger.info(f"{star} {msg_color}{user.display_name}{Fore.RESET} earns {msg_color}{amt} XP{Fore.RESET} for {reason_text}! {star}")
    current_color = current_color + 1
    if current_color >= len(xp_colors):
        current_color = 0
    user_xp_data = get_user_xp(user.id)
    user_xp = user_xp_data["xp"]
    next_level_xp = calculate_xp_for_next_level(user_xp_data["level"])
    #logger.info(f'User XP: {user_xp} User level: {user_xp_data["level"]} Next level XP: {next_level_xp}')
    if user_xp >= next_level_xp:
      try:
        await level_up_user(user, user_xp_data["level"]+1)
      except Exception as e:
        logger.info(f"Error trying to level up user: {e}")

# get_user_xp(discord_id)
# discord_id[required]: int
# Returns a users current XP
def get_user_xp(discord_id):
  db = getDB()
  query = db.cursor()
  sql = "SELECT level, xp FROM users WHERE discord_id = %s"
  vals = (discord_id,)
  query.execute(sql, vals)
  user_xp = query.fetchone()
  db.commit()
  query.close()
  db.close()
  return { "level": user_xp[0], "xp" : user_xp[1] }


def check_react_history(reaction:discord.Reaction, user:discord.User):
  db = getDB()
  query = db.cursor()
  sql = "SELECT id FROM reactions WHERE user_id = %s AND reaction = %s AND reaction_message_id = %s"
  vals = (user.id, f"{reaction}", reaction.message.id)
  query.execute(sql, vals)
  reaction_exists = query.fetchone()
  query.close()
  db.close()
  return reaction_exists

def log_react_history(reaction:discord.Reaction, user:discord.User):
  db = getDB()
  query = db.cursor()
  sql = "INSERT INTO reactions (user_id, user_name, reaction, reaction_message_id) VALUES (%s, %s, %s, %s)"
  vals = (user.id, user.display_name, f"{reaction}", reaction.message.id)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()

# log_xp_history(user_discord_id:int, amt:int, channel_name:str, reason:str)
# user_discord_id[required]: int
# amt[required]: int
# channel_id[required]: int
# reason[required]: str
# This function will log xp gains to a table for reporting
def log_xp_history(user_discord_id:int, amt:int, channel_id:int, reason:str):
  db = getDB()
  query = db.cursor()
  sql = "INSERT INTO xp_history (user_discord_id, amount, channel_id, reason) VALUES (%s, %s, %s, %s)"
  vals = (user_discord_id, amt, channel_id, reason)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()