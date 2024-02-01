from common import *

def db_get_current_xp_enabled_value(user_id):
  with AgimusDB(dictionary=True) as query:
    sql = "SELECT xp_enabled FROM users WHERE discord_id = %s"
    vals = (user_id,)
    query.execute(sql, vals)
    row = query.fetchone()
  return row['xp_enabled']
