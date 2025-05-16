from common import *

from queries.badge_info import db_get_special_badge_info

async def db_orphan_badge_instances_by_prestige(user_id: int, prestige: int) -> int:
  async with AgimusDB() as db:
    if prestige == 0:
      # Preserve special badges at Standard tier
      special_badges = await db_get_special_badge_info()
      special_ids = [b['id'] for b in special_badges]
      if not special_ids:
        return 0
      fmt = ','.join(['%s'] * len(special_ids))
      sql = f'''
        UPDATE badge_instances
        SET owner_discord_id = NULL
        WHERE owner_discord_id = %s
          AND prestige_level = 0
          AND badge_info_id NOT IN ({fmt})
      '''
      params = [user_id] + special_ids
      result = await db.execute(sql, tuple(params))
    else:
      sql = '''
        UPDATE badge_instances
        SET owner_discord_id = NULL
        WHERE owner_discord_id = %s
          AND prestige_level = %s
      '''
      result = await db.execute(sql, (user_id, prestige))
  return result
