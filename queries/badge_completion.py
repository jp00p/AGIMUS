from common import *


# _________                       .__          __  .__
# \_   ___ \  ____   _____ ______ |  |   _____/  |_|__| ____   ____
# /    \  \/ /  _ \ /     \\____ \|  | _/ __ \   __\  |/  _ \ /    \
# \     \___(  <_> )  Y Y  \  |_> >  |_\  ___/|  | |  (  <_> )   |  \
#  \______  /\____/|__|_|  /   __/|____/\___  >__| |__|\____/|___|  /
#         \/             \/|__|             \/                    \/
async def db_completion_by_affiliation(user_id, prestige: int | None = None):
  query = '''
    SELECT
      affiliation_name AS name,
      count(DISTINCT b_i.badge_filename) as total,
      count(DISTINCT b.badge_info_id) as collected,
      CEIL(count(DISTINCT b.badge_info_id) * 100.0 / count(DISTINCT b_i.badge_filename)) as percentage
    FROM badge_info AS b_i
    INNER JOIN badge_affiliation AS b_a
      ON b_i.badge_filename = b_a.badge_filename
    LEFT JOIN badge_instances AS b
      ON b.badge_info_id = b_i.id
      AND b.owner_discord_id = %s
  '''
  params = [user_id]
  if prestige is not None:
    query += ' AND b.prestige_level = %s'
    params.append(prestige)

  query += '''
    GROUP BY b_a.affiliation_name
    ORDER BY percentage DESC, affiliation_name
  '''
  async with AgimusDB(dictionary=True) as db:
    await db.execute(query, tuple(params))
    return await db.fetchall()


async def db_completion_by_franchise(user_id, prestige: int | None = None):
  query = '''
    SELECT
      b_i.franchise AS name,
      count(DISTINCT b_i.badge_filename) as total,
      count(DISTINCT b.badge_info_id) as collected,
      CEIL(count(DISTINCT b.badge_info_id) * 100.0 / count(DISTINCT b_i.badge_filename)) as percentage
    FROM badge_info AS b_i
    LEFT JOIN badge_instances AS b
      ON b.badge_info_id = b_i.id
      AND b.owner_discord_id = %s
  '''
  params = [user_id]
  if prestige is not None:
    query += ' AND b.prestige_level = %s'
    params.append(prestige)

  query += '''
    GROUP BY b_i.franchise
    ORDER BY percentage DESC, b_i.franchise
  '''
  async with AgimusDB(dictionary=True) as db:
    await db.execute(query, tuple(params))
    return await db.fetchall()


async def db_completion_by_time_period(user_id, prestige: int | None = None):
  query = '''
    SELECT
      b_i.time_period AS name,
      count(DISTINCT b_i.badge_filename) as total,
      count(DISTINCT b.badge_info_id) as collected,
      CEIL(count(DISTINCT b.badge_info_id) * 100.0 / count(DISTINCT b_i.badge_filename)) as percentage
    FROM badge_info AS b_i
    LEFT JOIN badge_instances AS b
      ON b.badge_info_id = b_i.id
      AND b.owner_discord_id = %s
  '''
  params = [user_id]
  if prestige is not None:
    query += ' AND b.prestige_level = %s'
    params.append(prestige)

  query += '''
    GROUP BY b_i.time_period
    ORDER BY percentage DESC, b_i.time_period
  '''
  async with AgimusDB(dictionary=True) as db:
    await db.execute(query, tuple(params))
    return await db.fetchall()


async def db_completion_by_type(user_id, prestige: int | None = None):
  query = '''
    SELECT
      type_name AS name,
      count(DISTINCT b_i.badge_filename) as total,
      count(DISTINCT b.badge_info_id) as collected,
      CEIL(count(DISTINCT b.badge_info_id) * 100.0 / count(DISTINCT b_i.badge_filename)) as percentage
    FROM badge_info AS b_i
    INNER JOIN badge_type AS b_t
      ON b_i.badge_filename = b_t.badge_filename
    LEFT JOIN badge_instances AS b
      ON b.badge_info_id = b_i.id
      AND b.owner_discord_id = %s
  '''
  params = [user_id]
  if prestige is not None:
    query += ' AND b.prestige_level = %s'
    params.append(prestige)

  query += '''
    GROUP BY b_t.type_name
    ORDER BY percentage DESC, type_name
  '''
  async with AgimusDB(dictionary=True) as db:
    await db.execute(query, tuple(params))
    return await db.fetchall()
