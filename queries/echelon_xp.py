from common import *

async def db_get_echelon_progress(user_discord_id: str) -> dict:
  async with AgimusDB(dictionary=True) as db:
    await db.execute("SELECT * FROM echelon_progress WHERE user_discord_id = %s", (user_discord_id,))
    result = await db.fetchone()
    if not result:
      result = {
        'user_discord_id': user_discord_id,
        'current_xp': 0,
        'current_level': 0,
        'current_prestige_tier': 0,
        'buffer_failure_streak': 0
      }
    return result

async def db_update_echelon_progress(user_discord_id: str, new_xp: int, new_level: int):
  sql = """
    INSERT INTO echelon_progress (user_discord_id, current_xp, current_level)
    VALUES (%s, %s, %s) AS new
    ON DUPLICATE KEY UPDATE
      current_xp = new.current_xp,
      current_level = new.current_level,
      updated_at = CURRENT_TIMESTAMP
  """
  async with AgimusDB() as db:
    await db.execute(sql, (user_discord_id, new_xp, new_level))

async def db_insert_echelon_history(user_discord_id: str, xp_gained: int, user_level_at_gain: int, channel_id: int, reason: str):
  async with AgimusDB() as db:
    await db.execute(
      "INSERT INTO echelon_progress_history (user_discord_id, xp_gained, user_level_at_gain, channel_id, reason) VALUES (%s, %s, %s, %s, %s)",
      (user_discord_id, xp_gained, user_level_at_gain, channel_id, reason)
    )

async def db_set_user_prestige_level(user_discord_id: str, prestige_level: int):
  sql = """
    UPDATE echelon_progress
    SET current_prestige_tier = %s
    WHERE user_discord_id = %s
  """
  async with AgimusDB() as db:
    await db.execute(sql, (prestige_level, user_discord_id))

async def db_get_legacy_xp_data(user_discord_id: str) -> dict:
  async with AgimusDB(dictionary=True) as db:
    await db.execute("SELECT * FROM legacy_xp_records WHERE user_discord_id = %s", (user_discord_id,))
    return await db.fetchone()