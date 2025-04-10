from common import *

#   ________        __
#  /  _____/  _____/  |_
# /   \  ____/ __ \   __\
# \    \_\  \  ___/|  |
#  \______  /\___  >__|
#         \/     \/
async def db_get_user_wishlist_badges(user_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT * FROM badge_info AS b_i
        JOIN badge_wishlists AS b_w
        ON b_w.user_discord_id = %s AND b_i.badge_filename = b_w.badge_filename
        ORDER BY b_i.badge_name ASC
    '''
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    badges = await query.fetchall()
  return badges


async def get_user_wishlist_info_ids(user_id: int) -> list[int]:
  query = """
    SELECT badge_info_id
    FROM wishlist
    WHERE user_discord_id = %s
  """
  async with AgimusDB() as db:
    await db.execute(query, (user_id,))
    rows = await db.fetchall()
  return [row['badge_info_id'] for row in rows]

#    _____       .___  .___     /\ __________
#   /  _  \    __| _/__| _/    / / \______   \ ____   _____   _______  __ ____
#  /  /_\  \  / __ |/ __ |    / /   |       _// __ \ /     \ /  _ \  \/ // __ \
# /    |    \/ /_/ / /_/ |   / /    |    |   \  ___/|  Y Y  (  <_> )   /\  ___/
# \____|__  /\____ \____ |  / /     |____|_  /\___  >__|_|  /\____/ \_/  \___  >
#         \/      \/    \/  \/             \/     \/      \/                 \/
async def db_add_badge_name_to_users_wishlist(user_discord_id, badge_name):
  async with AgimusDB() as query:
    sql = '''
      INSERT INTO badge_wishlists (user_discord_id, badge_filename)
        VALUES (%s, (SELECT badge_filename FROM badge_info WHERE badge_name = %s))
    '''
    vals = (user_discord_id, badge_name)
    await query.execute(sql, vals)

async def db_add_badge_filenames_to_users_wishlist(user_discord_id, badge_filenames):
  badges_values_list = []
  for b in badge_filenames:
    tuple = (user_discord_id, b)
    badges_values_list.append(tuple)

  async with AgimusDB() as query:
    sql = '''
      INSERT INTO badge_wishlists (user_discord_id, badge_filename)
        VALUES (%s, %s)
    '''
    await query.executemany(sql, badges_values_list)

async def db_remove_badge_name_from_users_wishlist(user_discord_id, badge_name):
  async with AgimusDB() as query:
    sql = '''
      DELETE b_w FROM badge_wishlists AS b_w
        JOIN badge_info AS b_i
          ON b_w.badge_filename = b_i.badge_filename
        WHERE b_w.user_discord_id = %s AND b_i.badge_name = %s
    '''
    vals = (user_discord_id, badge_name)
    await query.execute(sql, vals)

async def db_remove_badge_filenames_from_users_wishlist(user_discord_id, badge_filenames):
  badges_values_list = []
  for b in badge_filenames:
    tuple = (user_discord_id, b)
    badges_values_list.append(tuple)

  async with AgimusDB() as query:
    sql = '''
      DELETE FROM badge_wishlists WHERE user_discord_id = %s AND badge_filename = %s
    '''
    await query.executemany(sql, badges_values_list)

async def db_clear_users_wishlist(user_discord_id):
  async with AgimusDB() as query:
    sql = '''
      DELETE FROM badge_wishlists WHERE user_discord_id = %s
    '''
    vals = (user_discord_id, )
    await query.execute(sql, vals)

async def db_purge_users_wishlist(user_discord_id: int):
  """
  Deletes all rows from `badge_wishlists` where the user already owns the badge.
  """
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      DELETE b_w FROM badge_wishlists AS b_w
        JOIN badge_info AS b_i
          ON b_w.badge_filename = b_i.badge_filename
        JOIN badge_instances AS b_inst
          ON b_inst.owner_discord_id = b_w.user_discord_id
         AND b_inst.badge_info_id = b_i.id
        WHERE b_w.user_discord_id = %s
    '''
    vals = (user_discord_id,)
    await query.execute(sql, vals)


# .____                  __         /\  ____ ___      .__                 __
# |    |    ____   ____ |  | __    / / |    |   \____ |  |   ____   ____ |  | __
# |    |   /  _ \_/ ___\|  |/ /   / /  |    |   /    \|  |  /  _ \_/ ___\|  |/ /
# |    |__(  <_> )  \___|    <   / /   |    |  /   |  \  |_(  <_> )  \___|    <
# |_______ \____/ \___  >__|_ \ / /    |______/|___|  /____/\____/ \___  >__|_ \
#         \/          \/     \/ \/                  \/                 \/     \/
async def db_autolock_badges_by_filenames_if_in_wishlist(user_discord_id, badge_filenames):
  badges_values_list = []
  for b in badge_filenames:
    badges_values_list.append((user_discord_id, b))

  async with AgimusDB() as query:
    sql = '''
      UPDATE badge_instances AS b
        JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
        JOIN badge_wishlists AS b_w
          ON b_w.user_discord_id = b.owner_discord_id AND b_i.badge_filename = b_w.badge_filename
        SET b.is_locked = 1
        WHERE b.owner_discord_id = %s AND b_i.badge_filename = %s
    '''
    await query.executemany(sql, badges_values_list)

async def db_get_badge_locked_status_by_name(user_discord_id, badge_name):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT b_i.*, b.is_locked AS locked FROM badge_info AS b_i
        JOIN badge_instances AS b
          ON b.badge_info_id = b_i.id
        WHERE b.owner_discord_id = %s AND b_i.badge_name = %s
    '''
    vals = (user_discord_id, badge_name)
    await query.execute(sql, vals)
    results = await query.fetchone()
  return results

async def db_lock_badge_by_filename(user_discord_id, badge_filename):
  async with AgimusDB() as query:
    sql = '''
      UPDATE badge_instances AS b
        JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
        SET b.is_locked = 1
        WHERE b.owner_discord_id = %s AND b_i.badge_filename = %s
    '''
    await query.execute(sql, (user_discord_id, badge_filename))

async def db_lock_badges_by_filenames(user_discord_id, badge_filenames):
  badges_values_list = [(user_discord_id, b) for b in badge_filenames]
  async with AgimusDB() as query:
    sql = '''
      UPDATE badge_instances AS b
        JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
        SET b.is_locked = 1
        WHERE b.owner_discord_id = %s AND b_i.badge_filename = %s
    '''
    await query.executemany(sql, badges_values_list)

async def db_unlock_badge_by_filename(user_discord_id, badge_filename):
  async with AgimusDB() as query:
    sql = '''
      UPDATE badge_instances AS b
        JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
        SET b.is_locked = 0
        WHERE b.owner_discord_id = %s AND b_i.badge_filename = %s
    '''
    await query.execute(sql, (user_discord_id, badge_filename))

async def db_unlock_badges_by_filenames(user_discord_id, badge_filenames):
  badges_values_list = [(user_discord_id, b) for b in badge_filenames]
  async with AgimusDB() as query:
    sql = '''
      UPDATE badge_instances AS b
        JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
        SET b.is_locked = 0
        WHERE b.owner_discord_id = %s AND b_i.badge_filename = %s
    '''
    await query.executemany(sql, badges_values_list)


#    _____          __         .__
#   /     \ _____ _/  |_  ____ |  |__   ____   ______
#  /  \ /  \\__  \\   __\/ ___\|  |  \_/ __ \ /  ___/
# /    Y    \/ __ \|  | \  \___|   Y  \  ___/ \___ \
# \____|__  (____  /__|  \___  >___|  /\___  >____  >
#         \/     \/          \/     \/     \/     \/
async def db_get_wishlist_matches(user_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT b_i.*, b.owner_discord_id AS user_discord_id FROM badge_info AS b_i
        JOIN badge_instances AS b ON b.badge_info_id = b_i.id
        WHERE b_i.badge_filename IN (
          SELECT badge_filename FROM badge_wishlists WHERE user_discord_id = %s
        ) AND NOT b.is_locked
    '''
    await query.execute(sql, (user_discord_id,))
    return await query.fetchall()


async def db_get_wishlist_badge_matches(badge_filename):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT badge_filename, user_discord_id FROM badge_wishlists where badge_filename = %s
    '''
    vals = (badge_filename,)
    await query.execute(sql, vals)
    results = await query.fetchall()
  return results

async def db_get_wishlist_inventory_matches(user_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT b_i.*, b_w.user_discord_id FROM badge_info AS b_i
        JOIN badge_wishlists AS b_w
          ON b_w.badge_filename = b_i.badge_filename
        JOIN badge_instances AS b
          ON b.badge_info_id = b_i.id
        WHERE b.owner_discord_id = %s AND NOT b.is_locked
    '''
    await query.execute(sql, (user_discord_id,))
    return await query.fetchall()


# ________  .__               .__                      .__
# \______ \ |__| ______ _____ |__| ______ ___________  |  |   ______
#  |    |  \|  |/  ___//     \|  |/  ___//  ___/\__  \ |  |  /  ___/
#  |    `   \  |\___ \|  Y Y  \  |\___ \ \___ \  / __ \|  |__\___ \
# /_______  /__/____  >__|_|  /__/____  >____  >(____  /____/____  >
#         \/        \/      \/        \/     \/      \/          \/
async def db_get_wishlist_dismissal(user_discord_id, match_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT * FROM wishlist_dismissals WHERE user_discord_id = %s AND match_discord_id = %s LIMIT 1;
    '''
    vals = (user_discord_id, match_discord_id)
    await query.execute(sql, vals)
    results = await query.fetchone()
  return results

async def db_get_all_users_wishlist_dismissals(user_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT * FROM wishlist_dismissals WHERE user_discord_id = %s;
    '''
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    results = await query.fetchall()
  return results

async def db_delete_wishlist_dismissal(user_discord_id, match_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      DELETE FROM wishlist_dismissals WHERE user_discord_id = %s AND match_discord_id = %s;
    '''
    vals = (user_discord_id, match_discord_id)
    await query.execute(sql, vals)

async def db_add_wishlist_dismissal(user_discord_id, match_discord_id, has, wants):
  async with AgimusDB() as query:
    sql = '''
      INSERT INTO wishlist_dismissals (user_discord_id, match_discord_id, has, wants)
        VALUES (%s, %s, %s, %s)
    '''
    vals = (user_discord_id, match_discord_id, has, wants)
    await query.execute(sql, vals)
