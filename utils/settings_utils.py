from common import *

async def db_get_current_xp_enabled_value(user_id):
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT xp_enabled FROM users WHERE discord_id = %s"
    vals = (user_id,)
    await query.execute(sql, vals)
    row = await query.fetchone()
  return row['xp_enabled']
