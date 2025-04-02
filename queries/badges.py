from common import *

# BADGE INVENTORIES

async def db_get_total_badge_count_by_filename(filename):
  """
  Given the name of a badge, retrieves number that currently are in users collections
  :param name: the name of the badge.
  :return: row dict
  """
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT count(*) FROM badges WHERE badge_filename = %s;"
    vals = (filename,)
    await query.execute(sql, vals)
    row = await query.fetchone()
  return row["count(*)"]

async def db_get_user_badge_count(user_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT COUNT(*) as count FROM badges WHERE user_discord_id = %s"
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    result = await query.fetchone()
  return result['count']

async def db_get_user_badges(user_discord_id:int, sortby=None):
  '''
    get_user_badges(user_discord_id)
    user_discord_id[required]: int
    returns a list of badges the user has
  '''
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT b_i.badge_name, b_i.badge_filename, b.locked, b_i.special FROM badges b
        JOIN badge_info AS b_i
          ON b.badge_filename = b_i.badge_filename
          WHERE b.user_discord_id = %s
    '''
    order_by = " ORDER BY b_i.badge_filename ASC"
    if sortby is not None:
      if sortby == 'date_ascending':
        order_by = " ORDER BY b.time_created ASC, b_i.badge_filename ASC"
      elif sortby == 'date_descending':
        order_by = " ORDER BY b.time_created DESC, b_i.badge_filename ASC"
      elif sortby == 'locked_first':
        order_by = " ORDER BY b.locked ASC, b_i.badge_filename ASC"
      elif sortby == 'special_first':
        order_by = " ORDER BY b_i.special ASC, b_i.badge_filename ASC"
    sql = sql + order_by
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    badges = await query.fetchall()
  return badges

async def db_get_user_unlocked_badges(user_discord_id:int):
  '''
    db_get_user_unlocked_badges(user_discord_id)
    user_discord_id[required]: int
    returns a list of unlocked badges the user has
  '''
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT b_i.*, b.locked FROM badges b
        JOIN badge_info AS b_i
          ON b.badge_filename = b_i.badge_filename
          WHERE b.user_discord_id = %s AND b.locked = 0 AND b_i.special = 0
          ORDER BY b_i.badge_filename ASC
    '''
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    badges = await query.fetchall()
  return badges

async def db_get_user_locked_badges(user_discord_id:int):
  '''
    db_get_user_locked_badges(user_discord_id)
    user_discord_id[required]: int
    returns a list of unlocked badges the user has
  '''
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT b_i.*, b.locked FROM badges b
        JOIN badge_info AS b_i
          ON b.badge_filename = b_i.badge_filename
          WHERE b.user_discord_id = %s AND b.locked = 1 AND b_i.special = 0
          ORDER BY b_i.badge_filename ASC
    '''
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    badges = await query.fetchall()
  return badges

async def db_get_user_special_badges(user_discord_id:int):
  '''
    get_user_special_badges(user_discord_id)
    user_discord_id[required]: int
    returns a list of special badges the user has
  '''
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT b_i.*, b.locked FROM badges b
        JOIN badge_info AS b_i
          ON b.badge_filename = b_i.badge_filename
          WHERE b.user_discord_id = %s AND b_i.special = 1
          ORDER BY b_i.badge_filename ASC
    '''
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    badges = await query.fetchall()
  return badges

async def db_get_badge_count_for_user(user_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT count(*) FROM badges WHERE user_discord_id = %s
    '''
    vals = (user_id,)
    await query.execute(sql, vals)
    result = await query.fetchone()
  return result['count(*)']


#   _________                    .__       .__ __________             .___
#  /   _____/_____   ____   ____ |__|____  |  |\______   \_____     __| _/ ____   ____   ______
#  \_____  \\____ \_/ __ \_/ ___\|  \__  \ |  | |    |  _/\__  \   / __ | / ___\_/ __ \ /  ___/
#  /        \  |_> >  ___/\  \___|  |/ __ \|  |_|    |   \ / __ \_/ /_/ |/ /_/  >  ___/ \___ \
# /_______  /   __/ \___  >\___  >__(____  /____/______  /(____  /\____ |\___  / \___  >____  >
#         \/|__|        \/     \/        \/            \/      \/      \/_____/      \/     \/
_SPECIAL_BADGES = None
async def db_get_special_badges():
  global _SPECIAL_BADGES

  if _SPECIAL_BADGES is not None:
    return _SPECIAL_BADGES
  """
  Return all badge_info rows where special = 1
  :return:
  """
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT * FROM badge_info WHERE special = 1;"
    vals = ()
    await query.execute(sql, vals)
    rows = await query.fetchall()
  _SPECIAL_BADGES = rows
  return _SPECIAL_BADGES

