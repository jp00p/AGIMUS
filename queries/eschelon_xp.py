from common import *

async def db_get_eschelon_progress(user_discord_id: str) -> dict:
  async with AgimusDB(dictionary=True) as db:
    await db.execute("SELECT * FROM eschelon_progress WHERE user_discord_id = %s", (user_discord_id,))
    return await db.fetchone()

async def db_update_eschelon_progress(user_discord_id: str, new_xp: int, new_level: int):
  async with AgimusDB() as db:
    await db.execute(
      "REPLACE INTO eschelon_progress (user_discord_id, current_xp, current_level) VALUES (%s, %s, %s)",
      (user_discord_id, new_xp, new_level)
    )

async def db_insert_eschelon_history(user_discord_id: str, xp_gained: int, user_level_at_gain: int, channel_id: int, reason: str):
  async with AgimusDB() as db:
    await db.execute(
      "INSERT INTO eschelon_progress_history (user_discord_id, xp_gained, user_level_at_gain, channel_id, reason) VALUES (%s, %s, %s, %s, %s)",
      (user_discord_id, xp_gained, user_level_at_gain, channel_id, reason)
    )

async def db_set_user_prestige_level(user_discord_id: str, prestige_level: int):
  sql = """
    UPDATE eschelon_progress
    SET current_prestige_level = %s
    WHERE user_discord_id = %s
  """
  async with AgimusDB() as db:
    await db.execute(sql, (prestige_level, user_discord_id))