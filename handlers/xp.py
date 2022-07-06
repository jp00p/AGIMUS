from common import *

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

# handle_message_xp(message) - calculates xp for a given message
# message[required]: discord.Message
async def handle_message_xp(message:discord.Message):
    global current_color
    
    # we don't like bots round here
    if message.author.bot:
      return

    # Base XP to Grant
    xp_amt = 0
    # if the message is longer than 3 words +1 xp
    if len(message.content.split()) >= 3:
      xp_amt += 1
      # if that message also has any of our emoji, +1 xp
      for e in config["all_emoji"]:
        if message.content.find(e) != -1:
          xp_amt += 1
          break

    # if the message is longer than 33 words +1 xp
    if len(message.content.split()) > 33:
      xp_amt += 1

    # ...and 66, +1 more
    if len(message.content.split()) > 66:
      xp_amt += 1

    # if there's an attachment, +1 xp
    if len(message.attachments) > 0:
      xp_amt += 1 

    if xp_amt != 0:
      msg_color = xp_colors[current_color]
      star = f"{msg_color}{Style.BRIGHT}*{Style.NORMAL}{Fore.RESET}"
      logger.info(f"{star} {msg_color}{message.author.display_name}{Fore.RESET} earns {msg_color}{xp_amt} XP{Fore.RESET} {star}")

      increment_user_xp(message.author, xp_amt, "message", message.channel.name) # commit the xp gain to the db

      current_color = current_color + 1
      if current_color >= len(xp_colors):
        current_color = 0

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
      welcome_reacts = [EMOJI["ben_wave"], EMOJI["adam_wave"]]
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

  user_xp = get_user_xp(message.author.id)

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



async def handle_react_xp(reaction:discord.Reaction, user:discord.User):
  # Check if this user has already reacted to this message with this emoji

  if reaction.message.author.bot or user.bot:
    return

  global current_color
  msg_color = xp_colors[current_color]
  star = f"{msg_color}{Style.BRIGHT}*{Style.NORMAL}{Fore.RESET}"

  reaction_already_counted = check_react_history(reaction, user)
  if reaction_already_counted:
    #logger.info(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}{user.display_name}{Style.RESET_ALL} has {Fore.RED}already reacted{Fore.RESET} to {Style.BRIGHT}Message #{reaction.message.id}{Style.RESET_ALL} with {Style.BRIGHT}{reaction.emoji.name}{Style.RESET_ALL} previously!")
    return
  
  # If reaction hasn't been logged already, go ahead and do so and then award some XP!
  logger.info(f"{star} {msg_color}{user.display_name}{Fore.RESET} earns {msg_color}1 XP{Fore.RESET} for reacting to a message! {star}")
  log_react_history(reaction, user)
  increment_user_xp(user, 1, "reacted", reaction.message.channel.name)

  # Give the author some bonus XP if they've made a particularly reaction-worthy message!
  threshold_relevant_emojis = [
    config["emojis"]["data_lmao_lol"],
    config["emojis"]["picard_yes_happy_celebrate"],
    config["emojis"]["tgg_love_heart"]
  ]

  xp_amt = 0
  if f"{reaction.emoji}" in threshold_relevant_emojis and reaction.count >= 5 and reaction.count < 10:
    logger.info(f"{star} {msg_color}{reaction.message.author.display_name}{Fore.RESET} gets {msg_color}1 XP{Fore.RESET} for their message being reaction-worthy! {star}")
    xp_amt = 1
  
  if f"{reaction.emoji}" in threshold_relevant_emojis and reaction.count >= 10 and reaction.count < 20:
    logger.info(f"{star} {msg_color}{reaction.message.author.display_name}{Fore.RESET} gets {msg_color}2 XP{Fore.RESET} for posting a very-well reacted-to message! {star}")
    xp_amt = 2

  if f"{reaction.emoji}" in threshold_relevant_emojis and reaction.count >= 20:
    logger.info(f"{star} {msg_color}{reaction.message.author.display_name}{Fore.RESET} gets {msg_color}2 XP{Fore.RESET} for posting an {Style.BRIGHT} ULTRA REACTED-TO {Style.NORMAL}message! {star}")
    #logger.info(f"{Back.LIGHTBLACK_EX}{Fore.CYAN}User {Style.BRIGHT}{reaction.message.author.display_name}{Style.RESET_ALL} gets {Style.BRIGHT}5 xp{Style.RESET_ALL} for their message being {Fore.CYAN}{Style.BRIGHT}**ULTRA**{Style.RESET_ALL} reaction-worthy!")
    xp_amt = 5

  if xp_amt > 0:
    increment_user_xp(reaction.message.author, xp_amt, "reactions", reaction.message.channel.name)

  current_color = current_color + 1
  if current_color >= len(xp_colors):
      current_color = 0



# increment_user_xp(author, amt)
# messauge.author[required]: discord.User
# amt[required]: int
# This function will increment a users' XP and log the gain to the history
def increment_user_xp(user, amt, reason, channel_name):
  db = getDB()
  query = db.cursor()
  sql = "UPDATE users SET xp = xp + %s, name = %s WHERE discord_id = %s"
  vals = (amt, user.display_name, user.id)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()
  log_xp_history(user.id, amt, channel_name, reason)

# get_user_xp(discord_id)
# discord_id[required]: int
# Returns a users current XP
def get_user_xp(discord_id):
  db = getDB()
  query = db.cursor()
  sql = "SELECT xp FROM users WHERE discord_id = %s"
  vals = (discord_id,)
  query.execute(sql, vals)
  user_xp = query.fetchone()
  db.commit()
  query.close()
  db.close()
  return user_xp[0]


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
# channel_name[required]: str 
# reason[required]: str
# This function will log xp gains to a table for reporting
def log_xp_history(user_discord_id:int, amt:int, channel_name:str, reason:str):
  db = getDB()
  query = db.cursor()
  sql = "INSERT INTO xp_history (user_discord_id, amount, channel_name, reason) VALUES (%s, %s, %s, %s)"
  vals = (user_discord_id, amt, channel_name, reason)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()