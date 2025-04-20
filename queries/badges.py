from common import *

# BADGE INVENTORIES
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

async def db_get_badge_instances_count_for_user(user_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT count(*) FROM badges WHERE user_discord_id = %s
    '''
    vals = (user_id,)
    await query.execute(sql, vals)
    result = await query.fetchone()
  return result['count(*)']
