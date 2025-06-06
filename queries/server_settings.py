from common import *

# Admin Server Settings
async def db_get_server_settings() -> dict:
  async with AgimusDB(dictionary=True) as db:
    await db.execute("SELECT * FROM server_settings LIMIT 1")
    return await db.fetchone()

async def db_toggle_bonus_xp(value: bool):
  async with AgimusDB() as db:
    await db.execute(
      "UPDATE server_settings SET bonus_xp_enabled = %s WHERE id = 1",
      (value,)
    )

async def db_set_bonus_xp(value: bool):
  async with AgimusDB() as db:
    await db.execute(
      "UPDATE server_settings SET bonus_xp_amount  = %s WHERE id = 1",
      (value,)
    )