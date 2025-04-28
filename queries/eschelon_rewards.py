# utils/badge_rewards.py
from common import *

EMBARGO_DAYS = 30

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

async def db_get_user_embargoed_badges(user_discord_id: str, prestige_level: int) -> dict[int, datetime]:
  sql = """
    SELECT badge_info_id, traded_at
    FROM badge_embargoes
    WHERE user_discord_id = %s AND prestige_level = %s
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (user_discord_id, prestige_level))
    results = await db.fetchall()
    return {row['badge_info_id']: row['traded_at'] for row in results}

async def db_create_embargo_for_badge_instance(badge_instance_id: int):
  """
  Creates an embargo for a badge instance by looking up its badge_info_id and prestige_level,
  and inserting it into badge_embargoes.
  """
  sql = """
    INSERT INTO badge_embargoes (user_discord_id, badge_info_id, prestige_level, traded_at)
    SELECT owner_discord_id, badge_info_id, prestige_level, NOW()
    FROM badge_instances
    WHERE id = %s
  """
  async with AgimusDB() as db:
    await db.execute(sql, (badge_instance_id,))

async def db_cleanup_expired_embargoes(user_discord_id: str):
  sql = """
    DELETE FROM badge_embargoes
    WHERE user_discord_id = %s AND traded_at < (NOW() - INTERVAL %s DAY)
  """
  async with AgimusDB() as db:
    await db.execute(sql, (user_discord_id, EMBARGO_DAYS))


async def db_update_buffer_failure_streak(user_discord_id: str, new_streak: int):
  sql = """
    UPDATE eschelon_progress
    SET buffer_failure_streak = %s
    WHERE user_discord_id = %s
  """
  async with AgimusDB() as db:
    await db.execute(sql, (new_streak, user_discord_id))