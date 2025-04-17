from common import *


async def db_get_valid_reward_filenames(user_id: int):
  async with AgimusDB(dictionary=True) as query:
    sql = """
      SELECT badge_filename
      FROM badge_info
      WHERE special = FALSE
        AND id NOT IN (
          SELECT badge_info_id
          FROM badge_instances
          WHERE owner_discord_id = %s AND active = TRUE
        )
    """
    await query.execute(sql, (user_id,))
    rows = await query.fetchall()
  return [row['badge_filename'] for row in rows]

