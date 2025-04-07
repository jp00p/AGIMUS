from common import *


async def db_get_user_badges(user_id: int, sortby: str = None):
  sort_sql = "ORDER BY b_i.badge_filename ASC"
  if sortby is not None:
    if sortby == 'date_ascending':
      sort_sql = "ORDER BY b.time_awarded ASC, b_i.badge_filename ASC"
    elif sortby == 'date_descending':
      sort_sql = "ORDER BY b.time_awarded DESC, b_i.badge_filename ASC"
    elif sortby == 'locked_first':
      sort_sql = "ORDER BY b.locked ASC, b_i.badge_filename ASC"
    elif sortby == 'special_first':
      sort_sql = "ORDER BY b_i.special ASC, b_i.badge_filename ASC"

  async with AgimusDB(dictionary=True) as query:
    await query.execute(
      f"""
        SELECT
          b_i.*,
          b.locked,
          b.id AS badge_instance_id,
          b.preferred_crystal_id,

          c.id AS crystal_id,
          c.crystal_type_id,
          t.name AS crystal_name,
          t.effect,
          t.crystal_rarity_rank

        FROM badge_instances AS b
        JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
        LEFT JOIN badge_crystals AS c ON b.preferred_crystal_id = c.id
        LEFT JOIN crystal_types AS t ON c.crystal_type_id = t.id
        WHERE b.owner_discord_id = %s
        {sort_sql}
      """,
      (user_id,)
    )
    return await query.fetchall()


async def db_get_badge_instance(user_id, badge_info_id):
  async with AgimusDB(dictionary=True) as query:
    await query.execute(
      "SELECT id FROM badge_instances WHERE badge_info_id = %s AND owner_discord_id = %s",
      (badge_info_id, user_id)
    )
    instance = await query.fetchone()
  return instance


async def db_create_badge_instance_if_missing(user_id: int, badge_info_id: int):
  async with AgimusDB(dictionary=True) as query:
    await query.execute(
      "SELECT id FROM badge_instances WHERE badge_info_id = %s AND owner_discord_id = %s",
      (badge_info_id, user_id)
    )
    existing = await query.fetchone()
    if existing:
      return None

    await query.execute(
      "INSERT INTO badge_instances (badge_info_id, owner_discord_id, locked) VALUES (%s, %s, %s)",
      (badge_info_id, user_id, False)
    )
    instance_id = query.lastrowid

    await query.execute("SELECT * FROM badge_instances WHERE id = %s", (instance_id,))
    instance = query.fetchone()
  return instance

