from typing import List

from utils.database import AgimusDB


def set_birthday(user_id: str, month: int, day: int):
  """
  Save the user’s birthday in the DB.  Replace so that it will update as well
  """
  with AgimusDB(dictionary=True) as conn:
    sql = "REPLACE INTO user_birthdays (user_discord_id, month, day) VALUES (%s, %s, %s)"
    vals = user_id, month, day
    conn.execute(sql, vals)


def clear_birthday(user_id: str):
  """
  Delete the user's birthday
  """
  with AgimusDB(dictionary=True) as conn:
    sql = "DELETE FROM user_birthdays WHERE user_discord_id = %s"
    vals = user_id,
    conn.execute(sql, vals)


def get_users_with_birthday(month: int, day: int) -> List[str]:
  """
  Get a list of discord IDs for users that have set their birthday
  """
  user_ids = []
  with AgimusDB(dictionary=True) as conn:
    sql = "SELECT user_discord_id FROM user_birthdays WHERE month = %s AND day = %s"
    vals = month, day
    conn.execute(sql, vals)
    result = conn.fetchall()
    for row in result:
      user_ids.append(row['user_discord_id'])
  
  return user_ids
