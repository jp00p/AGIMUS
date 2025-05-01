from common import *

from queries.badge_info import db_get_special_badge_info

async def db_delete_badge_instances_by_prestige(user_id: int, prestige: int) -> int:
  async with AgimusDB() as db:
    if prestige == 0:
      # Preserve special badges at Standard tier
      special_badges = await db_get_special_badge_info()
      special_ids = [b['id'] for b in special_badges]
      if not special_ids:
        return 0

      format_strings = ','.join(['%s'] * len(special_ids))
      sql = f'''
        DELETE FROM badge_instances
        WHERE owner_discord_id = %s
          AND prestige_level = 0
          AND badge_info_id NOT IN ({format_strings})
      '''
      params = [user_id] + special_ids
      result = await db.execute(sql, tuple(params))
    else:
      sql = '''
        DELETE FROM badge_instances
        WHERE owner_discord_id = %s
          AND prestige_level = %s
      '''
      result = await db.execute(sql, (user_id, prestige))

    return result.rowcount
