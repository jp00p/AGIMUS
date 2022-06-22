from .common import *

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

CADET_XP_REQUIREMENT    = 10
ENSIGN_XP_REQUIREMENT   = 16

# handle_message_xp(message) - calculates xp for a given message
# message[required]: discord.Message
async def handle_message_xp(message:discord.Message):

    # we don't like bots round here
    if message.author.bot:
      return

    global current_color

    xp_amt = 0

    # if the message is longer than 3 words +1 xp
    if len(message.content.split()) >= 3:
        xp_amt += 1
        # if that message also has any of our emoji, +1 xp
        for e in config["all_emoji"]:
            if message.content.find(e) != -1:
                xp_amt += 1
                break;

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

        increment_user_xp(message.author, xp_amt) # commit the xp gain to the db

        current_color = current_color + 1
        if current_color >= len(xp_colors):
            current_color = 0
        
        # handle role stuff
        cadet_role = discord.utils.get(message.author.guild.roles, id=config["roles"]["cadet"])
        ensign_role = discord.utils.get(message.author.guild.roles, id=config["roles"]["ensign"])
        user_xp = get_user_xp(message.author.id)

        # if they don't have cadet yet and they are over the required xp, give it to them
        if cadet_role not in message.author.roles:
            if user_xp >= CADET_XP_REQUIREMENT:
                await message.author.add_roles(cadet_role)
                logger.info(f"{Style.BRIGHT}{message.author.display_name}{Style.RESET_ALL} has been promoted to {Fore.CYAN}Cadet{Fore.RESET} via XP!")
        else:
        # if they do have cadet but not ensign yet, give it to them
            if ensign_role not in message.author.roles:
                if user_xp >= ENSIGN_XP_REQUIREMENT:
                    await message.author.add_roles(ensign_role)
                    logger.info(f"{Style.BRIGHT}{message.author.display_name}{Style.RESET_ALL} has been promoted to {Fore.GREEN}Ensign{Fore.RESET} via XP!")
        

# increment_user_xp(author, amt)
# messauge.author[required]: discord.User
# amt[required]: int
# This function will increment a users' XP
def increment_user_xp(user, amt):
  db = getDB()
  query = db.cursor()
  sql = "UPDATE users SET xp = xp + %s, name = %s WHERE discord_id = %s"
  vals = (amt, user.display_name, user.id)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()

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
  increment_user_xp(user, 1)

  # Give the author some bonus XP if they've made a particularly reaction-worthy message!
  threshold_relevant_emojis = [
    config["emojis"]["data_lmao_lol"],
    config["emojis"]["picard_yes_happy_celebrate"],
    config["emojis"]["tgg_love_heart"]
  ]
  if f"{reaction.emoji}" in threshold_relevant_emojis and reaction.count >= 5 and reaction.count < 10:
    logger.info(f"{star} {msg_color}{reaction.message.author.display_name}{Fore.RESET} gets {msg_color}1 XP{Fore.RESET} for their message being reaction-worthy! {star}")
    #logger.info(f"{Fore.LIGHTGREEN_EX}User {Style.BRIGHT}{reaction.message.author.display_name}{Style.RESET_ALL} gets {Fore.LIGHTGREEN_EX}{Style.BRIGHT}1 xp{Style.RESET_ALL} for their message being reaction-worthy!")
    increment_user_xp(reaction.message.author, 1)
  
  if f"{reaction.emoji}" in threshold_relevant_emojis and reaction.count >= 10 and reaction.count < 20:
    logger.info(f"{star} {msg_color}{reaction.message.author.display_name}{Fore.RESET} gets {msg_color}2 XP{Fore.RESET} for posting a very-well reacted-to message! {star}")
    #logger.info(f"{Fore.LIGHTBLUE_EX}User {Style.BRIGHT}{reaction.message.author.display_name}{Style.RESET_ALL} gets {Style.BRIGHT}2 xp{Style.RESET_ALL} for their message being {Fore.LIGHTBLUE_EX}{Style.BRIGHT}*particularly*{Style.RESET_ALL} reaction-worthy!")
    increment_user_xp(reaction.message.author, 2)

  if f"{reaction.emoji}" in threshold_relevant_emojis and reaction.count >= 20:
    logger.info(f"{star} {msg_color}{reaction.message.author.display_name}{Fore.RESET} gets {msg_color}2 XP{Fore.RESET} for posting an {Style.BRIGHT} ULTRA REACTED-TO {Style.NORMAL}message! {star}")
    #logger.info(f"{Back.LIGHTBLACK_EX}{Fore.CYAN}User {Style.BRIGHT}{reaction.message.author.display_name}{Style.RESET_ALL} gets {Style.BRIGHT}5 xp{Style.RESET_ALL} for their message being {Fore.CYAN}{Style.BRIGHT}**ULTRA**{Style.RESET_ALL} reaction-worthy!")
    increment_user_xp(reaction.message.author, 5)

  current_color = current_color + 1
  if current_color >= len(xp_colors):
      current_color = 0


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
