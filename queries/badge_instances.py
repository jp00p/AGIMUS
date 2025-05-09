from common import *

from queries.common import BADGE_INSTANCE_COLUMNS

# GET
async def db_get_user_badge_instance_names_and_ids(user_id: int):
  # Simpler DB that doesn't use a lot of joins against the crystal tables
  async with AgimusDB(dictionary=True) as query:
    await query.execute(
      f"""
        SELECT
          b.id AS badge_instance_id,
          b_i.badge_name
        FROM badge_instances AS b
        JOIN badge_info as b_i on b.badge_info_id = b_i.id
        WHERE b.owner_discord_id = %s
        ORDER BY b_i.badge_name ASC
      """,
      (user_id,)
    )
    return await query.fetchall()

async def db_get_user_badge_instances(
  user_id: int,
  *,
  prestige: int = 0,
  locked: bool | None = None,
  special: bool | None = None,
  sortby: str = None
):
  where_clauses = ["b.owner_discord_id = %s", "b.active = TRUE"]
  params = [user_id]

  if prestige is not None:
    where_clauses.append("b.prestige_level = %s")
    params.append(prestige)

  if locked is not None:
    where_clauses.append("b.locked = %s")
    params.append(locked)

  if special is not None:
    where_clauses.append("b_i.special = %s")
    params.append(special)

  where_sql = " AND ".join(where_clauses)

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
        SELECT {BADGE_INSTANCE_COLUMNS}
        FROM badge_instances AS b
        JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
        LEFT JOIN badge_crystals AS c ON b.active_crystal_id = c.id
        LEFT JOIN crystal_instances AS ci ON c.crystal_instance_id = ci.id
        LEFT JOIN crystal_types AS t ON ci.crystal_type_id = t.id
        WHERE {where_sql}
        {sort_sql}
      """,
      params
    )
    return await query.fetchall()

async def db_get_badge_instance_by_id(badge_instance_id):
  sql = f"""
    SELECT {BADGE_INSTANCE_COLUMNS}
    FROM badge_instances AS b
    JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
    LEFT JOIN badge_crystals AS c ON b.active_crystal_id = c.id
    LEFT JOIN crystal_instances AS ci ON c.crystal_instance_id = ci.id
    LEFT JOIN crystal_types AS t ON ci.crystal_type_id = t.id
    WHERE b.id = %s
    LIMIT 1
  """
  async with AgimusDB(dictionary=True) as query:
    await query.execute(sql, (badge_instance_id,))
    instance = await query.fetchone()
  return instance

async def db_get_badge_instance_by_filename(user_id: int, badge_filename: str, prestige: int | None = None):
  sql = f"""
    SELECT {BADGE_INSTANCE_COLUMNS}
    FROM badge_instances AS b
    JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
    LEFT JOIN badge_crystals AS c ON b.active_crystal_id = c.id
    LEFT JOIN crystal_instances AS ci ON c.crystal_instance_id = ci.id
    LEFT JOIN crystal_types AS t ON ci.crystal_type_id = t.id
    WHERE b_i.badge_filename = %s
      AND b.owner_discord_id = %s
  """
  params = [badge_filename, user_id]
  if prestige is not None:
    sql += " AND b.prestige_level = %s"
    params.append(prestige)

  sql += " LIMIT 1"
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, tuple(params))
    return await db.fetchone()

async def db_get_badge_instance_by_badge_info_id(user_id: int, badge_info_id: int, prestige: int | None = None):
  sql = f"""
    SELECT {BADGE_INSTANCE_COLUMNS}
    FROM badge_instances AS b
    JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
    LEFT JOIN badge_crystals AS c ON b.active_crystal_id = c.id
    LEFT JOIN crystal_instances AS ci ON c.crystal_instance_id = ci.id
    LEFT JOIN crystal_types AS t ON ci.crystal_type_id = t.id
    WHERE b.badge_info_id = %s AND b.owner_discord_id = %s
  """
  params = [badge_info_id, user_id]
  if prestige is not None:
    sql += " AND b.prestige_level = %s"
    params.append(prestige)

  sql += " LIMIT 1"
  async with AgimusDB(dictionary=True) as query:
    await query.execute(sql, tuple(params))
    return await query.fetchone()

async def db_get_badge_instance_id_by_badge_info_id(user_id: int, badge_info_id: int, prestige: int | None = None):
  sql = """
    SELECT id FROM badge_instances
    WHERE badge_info_id = %s AND owner_discord_id = %s
  """
  params = [badge_info_id, user_id]
  if prestige is not None:
    sql += " AND prestige_level = %s"
    params.append(prestige)

  async with AgimusDB(dictionary=True) as query:
    await query.execute(sql, tuple(params))
    return await query.fetchone()

async def db_get_badge_instance_by_badge_name(user_id: int, badge_name: str, prestige: int | None = None):
  sql = f"""
    SELECT {BADGE_INSTANCE_COLUMNS}
    FROM badge_instances AS b
    JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
    LEFT JOIN badge_crystals AS c ON b.active_crystal_id = c.id
    LEFT JOIN crystal_instances AS ci ON c.crystal_instance_id = ci.id
    LEFT JOIN crystal_types AS t ON ci.crystal_type_id = t.id
    WHERE b_i.badge_name = %s
      AND b.owner_discord_id = %s
  """
  params = [badge_name, user_id]
  if prestige is not None:
    sql += " AND b.prestige_level = %s"
    params.append(prestige)

  sql += " LIMIT 1"
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, tuple(params))
    return await db.fetchone()

async def db_get_owned_badge_filenames(user_id: int, prestige: int | None = None):
  sql = '''
    SELECT b_i.badge_filename
    FROM badge_instances b
    JOIN badge_info b_i ON b.badge_info_id = b_i.id
    WHERE b.owner_discord_id = %s
      AND b.prestige_level = %s
      AND b.active = TRUE
      AND b.locked = FALSE
  '''
  params = [user_id]
  if prestige is not None:
    sql += " AND inst.prestige_level = %s"
    params.append(prestige)

  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, tuple(params))
    return await db.fetchall()

# Crystal-based Badge Instance Queries
async def db_get_badges_without_crystal_type(user_id: int, crystal_type_id: int) -> list[dict]:
  sql = """
    SELECT
      b_i.id AS badge_info_id,
      b_i.badge_name,
      b_i.badge_filename,
      b_i.badge_url,

      b.id AS badge_instance_id,
      b.owner_discord_id,
      b.active_crystal_id

    FROM badge_instances b
    JOIN badge_info b_i ON b.badge_info_id = b_i.id

    WHERE b.owner_discord_id = %s
      AND b.id NOT IN (
        SELECT bc.badge_instance_id
        FROM badge_crystals bc
        JOIN crystal_instances ci ON bc.crystal_instance_id = ci.id
        WHERE ci.crystal_type_id = %s
      )
    ORDER BY b_i.badge_name ASC
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (user_id, crystal_type_id))
    return await db.fetchall()


async def db_get_user_badge_instances_with_attuned_crystals(user_id: int):
  # Simpler DB that doesn't use a lot of joins against the crystal tables
  async with AgimusDB(dictionary=True) as query:
    await query.execute(
      f"""
        SELECT
          b.id AS badge_instance_id,
          b_i.badge_name
        FROM badge_instances AS b
        JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
        WHERE b.owner_discord_id = %s
          AND EXISTS (
            SELECT 1
            FROM badge_crystals bc
            WHERE bc.badge_instance_id = b.id
          )
        ORDER BY b_i.badge_name ASC
      """,
      (user_id,)
    )
    return await query.fetchall()


async def db_get_unlocked_and_unattuned_badge_instances(user_id: int, prestige: int) -> list[dict]:
  """
  Returns all active, unlocked badge instances owned by the user at the given prestige level
  that have no crystals attached (attuned or harmonized).

  Used by Tongo for selection pools
  """
  sql = f"""
    SELECT {BADGE_INSTANCE_COLUMNS}
    FROM badge_instances AS b
    JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
    LEFT JOIN badge_crystals AS c ON b.id = c.badge_instance_id
    LEFT JOIN crystal_instances AS ci ON c.crystal_instance_id = ci.id
    LEFT JOIN crystal_types AS t ON ci.crystal_type_id = t.id
    WHERE b.owner_discord_id = %s
      AND b.active = TRUE
      AND b.locked = FALSE
      AND b.prestige_level = %s
      AND b.id NOT IN (
        SELECT badge_instance_id
        FROM badge_crystals
      )
    ORDER BY b_i.badge_filename ASC
  """

  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (user_id, prestige))
    return await db.fetchall()


# COUNTS
async def db_get_badge_instances_count_for_user(user_id: int, prestige: int | None = None) -> int:
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT COUNT(*) AS count
      FROM badge_instances
      WHERE owner_discord_id = %s
        AND active = TRUE
    '''
    vals = [user_id]

    if prestige is not None:
      sql += ' AND prestige_level = %s'
      vals.append(prestige)

    await query.execute(sql, tuple(vals))
    result = await query.fetchone()

  return result['count']


async def db_get_total_badge_instances_count_by_filename(filename: str) -> int:
  """
  Given the filename of a badge, returns how many active instances exist in all user collections.
  """
  async with AgimusDB(dictionary=True) as query:
    sql = """
      SELECT COUNT(*) AS count
      FROM badge_instances AS bi
      JOIN badge_info AS info ON bi.badge_info_id = info.id
      WHERE info.badge_filename = %s
        AND bi.active = TRUE
    """
    vals = (filename,)
    await query.execute(sql, vals)
    row = await query.fetchone()
  return row["count"]


# Direct DB Helpers for Badge Instances *If Missing*
# NOTE: These are primarily used for the v2.0 to v3.0 `badge` to `badge_instances` migration
# Use utils.badge_instances -> `create_new_badge_instance()` for normal badge_instance creation
async def db_create_badge_instance_if_missing(user_id: int, badge_filename: str):
  async with AgimusDB(dictionary=True) as query:
    # Get the badge_info.id from the filename
    await query.execute(
      "SELECT id FROM badge_info WHERE badge_filename = %s",
      (badge_filename,)
    )
    result = await query.fetchone()
    if not result:
      return None
    badge_info_id = result['id']

    # Check if user already owns an active instance of this badge
    await query.execute(
      """
        SELECT id FROM badge_instances
        WHERE badge_info_id = %s AND owner_discord_id = %s AND active = TRUE
      """,
      (badge_info_id, user_id)
    )
    existing = await query.fetchone()
    if existing:
      return None

    # Insert the new instance
    await query.execute(
      """
        INSERT INTO badge_instances (badge_info_id, owner_discord_id, locked)
        VALUES (%s, %s, FALSE)
      """,
      (badge_info_id, user_id)
    )
    instance_id = query.lastrowid

    # Return enriched instance
    # (Crystal Info will be missing but just returning keys by expected 'instance format')
    await query.execute(
      f"""
        SELECT {BADGE_INSTANCE_COLUMNS}
        FROM badge_instances AS b
        JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
        LEFT JOIN badge_crystals AS c ON b.active_crystal_id = c.id
        LEFT JOIN crystal_types AS t ON c.crystal_type_id = t.id
        WHERE b.id = %s
      """,
      (instance_id,)
    )
    return await query.fetchone()

# async def db_create_badge_instance_if_missing_by_name(user_id: int, badge_name: str):
#   async with AgimusDB(dictionary=True) as query:
#     # Get the badge_info.id from the filename
#     await query.execute(
#       "SELECT badge_filename FROM badge_info WHERE badge_name = %s",
#       (badge_name,)
#     )
#     result = await query.fetchone()
#     if not result:
#       return None
#   return await _db_create_badge_instance_if_missing(user_id, result['badge_filename'])

