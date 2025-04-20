from common import *

from queries.common import BADGE_INSTANCE_COLUMNS

# _________                         __                 __
# \_   ___ \  ____   ____   _______/  |______    _____/  |_  ______
# /    \  \/ /  _ \ /    \ /  ___/\   __\__  \  /    \   __\/  ___/
# \     \___(  <_> )   |  \\___ \  |  |  / __ \|   |  \  |  \___ \
#  \______  /\____/|___|  /____  > |__| (____  /___|  /__| /____  >
#         \/            \/     \/            \/     \/          \/
_MAX_BADGE_COUNT = None
async def db_get_max_badge_count():
  global _MAX_BADGE_COUNT

  if _MAX_BADGE_COUNT is not None:
    return _MAX_BADGE_COUNT
  """
  Return the total number of possible badges we have in the system
  :return:
  """
  _MAX_BADGE_COUNT = len(await db_get_all_badge_info())
  return _MAX_BADGE_COUNT


_ALL_BADGE_INFO = None
async def db_get_all_badge_info():
  global _ALL_BADGE_INFO
  """
  Returns all rows from badge_info table
  :return: list of row dicts
  """
  if _ALL_BADGE_INFO is not None:
    return _ALL_BADGE_INFO

  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT * FROM badge_info ORDER BY badge_name ASC;"
    await query.execute(sql)
    rows = await query.fetchall()
    _ALL_BADGE_INFO = rows
  return _ALL_BADGE_INFO


_SPECIAL_BADGE_INFO = None
async def db_get_special_badge_info():
  global _SPECIAL_BADGE_INFO
  """
  Returns all rows from badge_info table where special = 1
  :return: list of row dicts
  """
  if _SPECIAL_BADGE_INFO is not None:
    return _SPECIAL_BADGE_INFO

  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT * FROM badge_info WHERE special = 1 ORDER BY badge_name ASC;"
    await query.execute(sql)
    rows = await query.fetchall()
    _SPECIAL_BADGE_INFO = rows
  return _SPECIAL_BADGE_INFO


# ________                      .__
# \_____  \  __ __   ___________|__| ____   ______
#  /  / \  \|  |  \_/ __ \_  __ \  |/ __ \ /  ___/
# /   \_/.  \  |  /\  ___/|  | \/  \  ___/ \___ \
# \_____\ \_/____/  \___  >__|  |__|\___  >____  >
#        \__>           \/              \/     \/
async def db_get_badge_info_by_id(badge_info_id):
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT * FROM badge_info WHERE id = %s"
    await query.execute(sql, (badge_info_id,))
    return await query.fetchone()

async def db_get_badge_info_by_name(name):
  """
  Given the name of a badge, retrieves its information from badge_info
  :param name: the name of the badge.
  :return: row dict
  """
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT * FROM badge_info WHERE badge_name = %s;"
    vals = (name,)
    await query.execute(sql, vals)
    row = await query.fetchone()

  return row

async def db_get_badge_info_by_filename(filename):
  """
  Given the filename of a badge, retrieves its information from badge_info
  :param filename: the name of the badge.
  :return: row dict
  """
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT * FROM badge_info WHERE badge_filename = %s;"
    vals = (filename,)
    await query.execute(sql, vals)
    row = await query.fetchone()
  return row

async def db_get_badge_info_by_instance_id(instance_id: int) -> dict:
  query = """
    SELECT bi.*
    FROM badge_instances AS inst
    JOIN badge_info AS bi ON inst.badge_info_id = bi.id
    WHERE inst.id = %s
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(query, (instance_id,))
    return await db.fetchone()

async def db_get_badge_count_by_filename(filename):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT COUNT(*) AS count
      FROM badge_instances bi
      JOIN badge_info b ON bi.badge_info_id = b.id
      WHERE b.badge_filename = %s;
    '''
    await query.execute(sql, (filename,))
    row = await query.fetchone()
  return row['count']


# Affiliations
async def db_get_all_affiliations():
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT distinct(affiliation_name) FROM badge_affiliation;"
    await query.execute(sql)
    rows = await query.fetchall()

  affiliations = [r['affiliation_name'] for r in rows if r['affiliation_name'] is not None]
  affiliations.sort()
  return affiliations

async def db_get_all_affiliation_badges(affiliation):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT b_i.* FROM badge_info b_i
        JOIN badge_affiliation AS b_a
          ON b_i.badge_filename = b_a.badge_filename
        WHERE b_a.affiliation_name = %s
        ORDER BY b_i.badge_name ASC;
    '''
    vals = (affiliation,)
    await query.execute(sql, vals)
    rows = await query.fetchall()
  return rows

async def db_get_badge_affiliations_by_badge_name(name):
  """
  Given the name of a badge, retrieves the affiliation(s) associated with it
  :param name: the name of the badge.
  :return: list of row dicts
  """
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT affiliation_name FROM badge_affiliation b_a
      JOIN badge_info as b_i
        ON b_i.badge_filename = b_a.badge_filename
      WHERE badge_name = %s;
    '''
    vals = (name,)
    await query.execute(sql, vals)
    rows = await query.fetchall()
  return rows

# Affiliations - User Collection Queries
async def db_get_badges_user_has_from_affiliation(user_id, affiliation):
  async with AgimusDB(dictionary=True) as query:
    sql = f'''
      SELECT {BADGE_INSTANCE_COLUMNS} FROM badge_instances b
        JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
        LEFT JOIN badge_crystals c ON c.id = b.active_crystal_id
        LEFT JOIN crystal_types t ON c.crystal_type_id = t.id
        JOIN badge_affiliation AS b_a ON b_i.badge_filename = b_a.badge_filename
        WHERE b.owner_discord_id = %s
          AND b_a.affiliation_name = %s
        ORDER BY b_i.badge_name ASC;
    '''
    await query.execute(sql, (user_id, affiliation))
    return await query.fetchall()

async def db_get_random_badges_from_user_by_affiliations(user_id: int):
  async with AgimusDB(dictionary=True) as query:
    sql = f'''
      SELECT {BADGE_INSTANCE_COLUMNS}, b_a.affiliation_name
      FROM badge_instances b
      INNER JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
      LEFT JOIN badge_crystals c ON c.id = b.active_crystal_id
      LEFT JOIN crystal_types t ON c.crystal_type_id = t.id
      INNER JOIN badge_affiliation AS b_a ON b_i.badge_filename = b_a.badge_filename
      WHERE b.owner_discord_id = %s
      ORDER BY RAND()
    '''
    await query.execute(sql, (user_id,))
    rows = await query.fetchall()
    return {r['affiliation_name']: r['badge_filename'] for r in rows}

# Franchises
async def db_get_all_franchises():
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT distinct(franchise) FROM badge_info"
    await query.execute(sql)
    rows = await query.fetchall()
  franchises = [r['franchise'] for r in rows if r['franchise'] is not None]
  franchises.sort()
  return franchises

async def db_get_all_franchise_badges(franchise):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT * FROM badge_info
        WHERE franchise = %s
        ORDER BY badge_name ASC;
    '''
    vals = (franchise,)
    await query.execute(sql, vals)
    rows = await query.fetchall()
  return rows


# Franchises - User Collection Queries
async def db_get_badges_user_has_from_franchise(user_id, franchise):
  async with AgimusDB(dictionary=True) as query:
    sql = f'''
      SELECT {BADGE_INSTANCE_COLUMNS} FROM badge_instances b
        JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
        LEFT JOIN badge_crystals c ON c.id = b.active_crystal_id
        LEFT JOIN crystal_types t ON c.crystal_type_id = t.id
        WHERE b.owner_discord_id = %s
          AND b_i.franchise = %s
        ORDER BY b_i.badge_name ASC;
    '''
    await query.execute(sql, (user_id, franchise))
    return await query.fetchall()

async def db_get_random_badges_from_user_by_franchises(user_id: int):
  async with AgimusDB(dictionary=True) as query:
    sql = f'''
      SELECT {BADGE_INSTANCE_COLUMNS}
      FROM badge_instances b
      INNER JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
      LEFT JOIN badge_crystals c ON c.id = b.active_crystal_id
      LEFT JOIN crystal_types t ON c.crystal_type_id = t.id
      WHERE b.owner_discord_id = %s
      ORDER BY RAND()
    '''
    await query.execute(sql, (user_id,))
    rows = await query.fetchall()
    return {r['franchise']: r['badge_filename'] for r in rows}


# Time Periods
async def db_get_all_time_periods():
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT distinct(time_period) FROM badge_info"
    await query.execute(sql)
    rows = await query.fetchall()
  time_periods = [r['time_period'] for r in rows if r['time_period'] is not None]
  time_periods.sort(key=_time_period_sort)
  return time_periods

def _time_period_sort(time_period):
  """
  We may be dealing with time periods before 1000,
  so tack on a 0 prefix for these for proper sorting
  """
  if len(time_period) == 4:
    return f"0{time_period}"
  else:
    return time_period

async def db_get_all_time_period_badges(time_period):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT * FROM badge_info b_i
        WHERE time_period = %s
        ORDER BY badge_name ASC
    '''
    vals = (time_period,)
    await query.execute(sql, vals)
    rows = await query.fetchall()
  return rows

# Time Periods - User Collection Queries
async def db_get_badges_user_has_from_time_period(user_id, time_period):
  async with AgimusDB(dictionary=True) as query:
    sql = f'''
      SELECT {BADGE_INSTANCE_COLUMNS} FROM badge_instances b
        JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
        LEFT JOIN badge_crystals c ON c.id = b.active_crystal_id
        LEFT JOIN crystal_types t ON c.crystal_type_id = t.id
        WHERE b.owner_discord_id = %s
          AND b_i.time_period = %s
        ORDER BY b_i.badge_name ASC
    '''
    await query.execute(sql, (user_id, time_period))
    return await query.fetchall()

async def db_get_random_badges_from_user_by_time_periods(user_id: int):
  async with AgimusDB(dictionary=True) as query:
    sql = f'''
      SELECT {BADGE_INSTANCE_COLUMNS}, b_i.time_period
      FROM badge_instances b
      INNER JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
      LEFT JOIN badge_crystals c ON c.id = b.active_crystal_id
      LEFT JOIN crystal_types t ON c.crystal_type_id = t.id
      WHERE b.owner_discord_id = %s
      ORDER BY RAND()
    '''
    await query.execute(sql, (user_id,))
    rows = await query.fetchall()
    return {r['time_period']: r['badge_filename'] for r in rows}


# Types
async def db_get_all_types():
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT distinct(type_name) FROM badge_type"
    await query.execute(sql)
    rows = await query.fetchall()
  types = [r['type_name'] for r in rows if r['type_name'] is not None]
  types.sort()
  return types

async def db_get_all_type_badges(type):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT b_i.* FROM badge_info b_i
        JOIN badge_type AS b_t
          ON b_i.badge_filename = b_t.badge_filename
        WHERE b_t.type_name = %s
        ORDER BY b_i.badge_name ASC
    '''
    vals = (type,)
    await query.execute(sql, vals)
    rows = await query.fetchall()
  return rows

async def db_get_badge_types_by_badge_name(name):
  """
  Given the name of a badge, retrieves the types(s) associated with it
  :param name: the name of the badge.
  :return: list of row dicts
  """
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT type_name FROM badge_type b_t
      JOIN badge_info as b_i
        ON b_i.badge_filename = b_t.badge_filename
      WHERE badge_name = %s;
    '''
    vals = (name,)
    await query.execute(sql, vals)
    rows = await query.fetchall()
  return rows

# Types - User Collection Queries
async def db_get_badges_user_has_from_type(user_id, type):
  async with AgimusDB(dictionary=True) as query:
    sql = f'''
      SELECT {BADGE_INSTANCE_COLUMNS} FROM badge_instances b
        JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
        LEFT JOIN badge_crystals c ON c.id = b.active_crystal_id
        LEFT JOIN crystal_types t ON c.crystal_type_id = t.id
        JOIN badge_type AS b_t ON b_i.badge_filename = b_t.badge_filename
        WHERE b.owner_discord_id = %s
          AND b_t.type_name = %s
        ORDER BY b_i.badge_name ASC
    '''
    await query.execute(sql, (user_id, type))
    return await query.fetchall()

async def db_get_random_badges_from_user_by_types(user_id: int):
  async with AgimusDB(dictionary=True) as query:
    sql = f'''
      SELECT {BADGE_INSTANCE_COLUMNS}, b_t.type_name
      FROM badge_instances b
      INNER JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
      LEFT JOIN badge_crystals c ON c.id = b.active_crystal_id
      LEFT JOIN crystal_types t ON c.crystal_type_id = t.id
      INNER JOIN badge_type AS b_t ON b_i.badge_filename = b_t.badge_filename
      WHERE b.owner_discord_id = %s
      ORDER BY RAND()
    '''
    await query.execute(sql, (user_id,))
    rows = await query.fetchall()
    return {r['type_name']: r['badge_filename'] for r in rows}