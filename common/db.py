from typing import TypedDict

import discord
from colorama import Style, Fore

from common.logs import logger
from utils.database import AgimusDB


class FullUserData(TypedDict):
  id: int
  discord_id:int
  name:str
  mention:str
  score:int
  spins:int
  jackpots:int
  wager:int
  high_roller:bool
  xp:int
  log_messages:int
  xp_enabled:bool
  receive_notifications:bool
  loudbot_enabled:bool
  tagging_enabled:bool
  crystal_autoharmonize:bool
  pattern_buffer:bool
  ping_on_badge:bool
  wishlist_dm_enabled:bool

  user_stickers:list[dict[str,str]]
  badges:list[dict[str,str]]


async def get_user(discord_id:int) -> FullUserData:
  """
  This function will return a user's record from their id
  """
  async with AgimusDB(dictionary=True) as query:
    # get user basic info
    sql = """
      SELECT
        users.*,
        profile_photos.photo AS profile_photo,
        profile_taglines.tagline AS profile_tagline
      FROM users
        LEFT JOIN profile_taglines ON profile_taglines.user_discord_id = users.discord_id
        LEFT JOIN profile_photos ON profile_photos.user_discord_id = users.discord_id
      WHERE users.discord_id = %s
    """
    vals = (discord_id,)
    await query.execute(sql, vals)
    user_data = await query.fetchone()
    if user_data:
      # get user stickers
      sql = "SELECT sticker, position FROM profile_stickers WHERE user_discord_id = %s AND sticker IS NOT NULL"
      vals = (discord_id,)
      await query.execute(sql, vals)
      user_stickers = await query.fetchall()
      # get user featured badges
      sql = "SELECT badge_filename FROM profile_badges WHERE user_discord_id = %s AND badge_filename IS NOT NULL"
      vals = (discord_id,)
      await query.execute(sql, vals)
      user_badges = await query.fetchall()
      # close db
      user_data["stickers"] = user_stickers
      user_data["badges"] = user_badges
      logger.debug(f"USER DATA: {user_data}")
  return user_data


async def get_all_users() -> list[int]:
  """
  This function takes no arguments
  and returns a list of all user discord ids
  """
  async with AgimusDB(dictionary=True) as query:
    await query.execute("SELECT discord_id FROM users")
    users = [
      int(user['discord_id']) for user in await query.fetchall()
    ]
  return users


async def register_user(user: discord.User) -> int:
  """
  This function will insert a new user into the database
  """
  async with AgimusDB() as query:
    sql = "INSERT INTO users (discord_id, name, mention) VALUES (%s, %s, %s)"
    vals = (user.id, user.display_name, user.mention)
    await query.execute(sql, vals)
    logger.info(f"{Style.BRIGHT}Registering user to DB:{Style.RESET_ALL} {user.id} {user.display_name} {user.mention}")
  return int(user.id)


async def update_user(discord_id: int, key: str, value: str):
    """
    This function will update a specific value for a specific user
    """
    modifiable = ["score", "spins", "jackpots", "wager", "high_roller", "xp", "level", "profile_photo", "profile_sticker_1"]
    if key not in modifiable:
        logger.error(f"{Fore.RED}{key} not in {modifiable}{Fore.RESET}")
    else:
        async with AgimusDB() as query:
            if key == "score":
                sql = "UPDATE users SET score = %s WHERE discord_id = %s"
            elif key == "spins":
                sql = "UPDATE users SET spins = %s WHERE discord_id = %s"
            elif key == "jackpots":
                sql = "UPDATE users SET jackpots = %s WHERE discord_id = %s"
            elif key == "wager":
                sql = "UPDATE users SET wager = %s WHERE discord_id = %s"
            elif key == "high_roller":
                sql = "UPDATE users SET high_roller = %s WHERE discord_id = %s"
            elif key == "profile_photo":
                sql = "UPDATE users SET profile_photo = %s WHERE discord_id = %s"
            elif key == "profile_sticker_1":
                sql = "UPDATE users SET profile_sticker_1 = %s WHERE discord_id = %s"
            elif key == "xp":
                sql = "UPDATE users SET xp = %s WHERE discord_id = %s"
            elif key == "level":
                sql = "UPDATE users SET level = %s WHERE discord_id = %s"
            vals = (value, discord_id)
            await query.execute(sql, vals)
            
            


