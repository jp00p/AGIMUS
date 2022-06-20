from .common import *

xp_colors = [
    Fore.CYAN,
    Fore.GREEN,
    Fore.LIGHTBLUE_EX,
    Fore.LIGHTCYAN_EX,
    Fore.LIGHTGREEN_EX,
    Fore.LIGHTMAGENTA_EX,
    Fore.LIGHTRED_EX,
    Fore.LIGHTWHITE_EX,
    Fore.LIGHTYELLOW_EX,
    Fore.MAGENTA,
    Fore.RED,
    Fore.YELLOW
]

CADET_XP_REQUIREMENT    = 10
ENSIGN_XP_REQUIREMENT   = 16

# handle_message_xp(message) - calculates xp for a given message
# message[required]: discord.Message
async def handle_message_xp(message:discord.Message):

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
        msg_colors = random.choices(xp_colors, k=2)
        
        logger.info(f"{msg_colors[0]}{Style.BRIGHT}{message.author.display_name}{Style.RESET_ALL}{Fore.RESET} earns {msg_colors[1]}{Style.BRIGHT}{xp_amt}{Style.RESET_ALL} XP{Fore.RESET}")
        increment_user_xp(message.author, xp_amt) # commit the xp gain to the db
        
        # handle role stuff
        cadet_role = discord.utils.get(message.author.guild.roles, id=config["roles"]["cadet"])
        ensign_role = discord.utils.get(message.author.guild.roles, id=config["roles"]["ensign"])
        user_xp = get_user_xp(message.author.id)

        # if they don't have cadet yet and they are over the required xp, give it to them
        if cadet_role not in message.author.roles:
            if user_xp >= CADET_XP_REQUIREMENT:
                await message.author.add_roles(cadet_role)
                logger.info(f"{Fore.CYAN}{Style.BRIGHT}{message.author.display_name}{Style.RESET_ALL} has been promoted to Cadet via XP!{Fore.RESET}")
        else:
        # if they do have cadet but not ensign yet, give it to them
            if ensign_role not in message.author.roles:
                if user_xp >= ENSIGN_XP_REQUIREMENT:
                    await message.author.add_roles(ensign_role)
                    logger.info(f"{Fore.GREEN}{Style.BRIGHT}{message.author.display_name}{Style.RESET_ALL} has been promoted to Ensign via XP!{Fore.RESET}")


# increment_user_xp(author, amt)
# messauge.author[required]: discord.User
# amt[required]: int
# This function will increment a users' XP
def increment_user_xp(user, amt):
  db = getDB()
  query = db.cursor()
  sql = "UPDATE users SET xp = xp + %s, name = %s WHERE discord_id = %s"
  vals = (amt,user.display_name, user.id)
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