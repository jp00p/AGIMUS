# utils/badge_rewards.py
from common import *

async def db_get_full_badge_info_pool() -> list[int]:
  sql = """
    SELECT id
    FROM badge_info
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql)
    results = await db.fetchall()
    return [row['id'] for row in results]

async def db_get_user_badges_at_prestige_level(user_discord_id: str, prestige_level: int) -> set[int]:
  sql = """
    SELECT badge_info_id
    FROM badge_instances
    WHERE owner_discord_id = %s AND prestige_level = %s
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (user_discord_id, prestige_level))
    results = await db.fetchall()
    return set(row['badge_info_id'] for row in results)

async def db_update_buffer_failure_streak(user_discord_id: str, new_streak: int):
  sql = """
    UPDATE echelon_progress
    SET buffer_failure_streak = %s
    WHERE user_discord_id = %s
  """
  async with AgimusDB() as db:
    await db.execute(sql, (new_streak, user_discord_id))