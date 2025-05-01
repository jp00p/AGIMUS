from common import *

async def db_delete_badge_instances_by_prestige(user_id: int, prestige: int) -> int:
  sql = '''
    DELETE FROM badge_instances
    WHERE owner_discord_id = %s
      AND prestige_level = %s
  '''
  async with AgimusDB() as db:
    result = await db.execute(sql, (user_id, prestige))
    return result.rowcount