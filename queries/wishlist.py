from common import *

#   ________        __
#  /  _____/  _____/  |_
# /   \  ____/ __ \   __\
# \    \_\  \  ___/|  |
#  \______  /\___  >__|
#         \/     \/
def db_get_user_wishlist_badges(user_discord_id):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT * FROM badge_info AS b_i
      JOIN badge_wishlists AS b_w
      ON b_w.user_discord_id = %s AND b_i.badge_filename = b_w.badge_filename
      ORDER BY b_i.badge_name ASC
  '''
  vals = (user_discord_id,)
  query.execute(sql, vals)
  badges = query.fetchall()
  query.close()
  db.close()
  return badges


#    _____       .___  .___     /\ __________
#   /  _  \    __| _/__| _/    / / \______   \ ____   _____   _______  __ ____
#  /  /_\  \  / __ |/ __ |    / /   |       _// __ \ /     \ /  _ \  \/ // __ \
# /    |    \/ /_/ / /_/ |   / /    |    |   \  ___/|  Y Y  (  <_> )   /\  ___/
# \____|__  /\____ \____ |  / /     |____|_  /\___  >__|_|  /\____/ \_/  \___  >
#         \/      \/    \/  \/             \/     \/      \/                 \/
def db_add_badge_name_to_users_wishlist(user_discord_id, badge_name):
  db = getDB()
  query = db.cursor()
  sql = '''
    INSERT INTO badge_wishlists (user_discord_id, badge_filename)
      VALUES (%s, (SELECT badge_filename FROM badge_info WHERE badge_name = %s))
  '''
  vals = (user_discord_id, badge_name)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()

def db_add_badge_filenames_to_users_wishlist(user_discord_id, badge_filenames):
  badges_values_list = []
  for b in badge_filenames:
    tuple = (user_discord_id, b)
    badges_values_list.append(tuple)

  db = getDB()
  query = db.cursor()
  sql = '''
    INSERT INTO badge_wishlists (user_discord_id, badge_filename)
      VALUES (%s, %s)
  '''
  query.executemany(sql, badges_values_list)
  db.commit()
  query.close()
  db.close()

def db_remove_badge_name_from_users_wishlist(user_discord_id, badge_name):
  db = getDB()
  query = db.cursor()
  sql = '''
    DELETE b_w FROM badge_wishlists AS b_w
      JOIN badge_info AS b_i
        ON b_w.badge_filename = b_i.badge_filename
      WHERE b_w.user_discord_id = %s AND b_i.badge_name = %s
  '''
  vals = (user_discord_id, badge_name)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()

def db_remove_badge_filenames_from_users_wishlist(user_discord_id, badge_filenames):
  badges_values_list = []
  for b in badge_filenames:
    tuple = (user_discord_id, b)
    badges_values_list.append(tuple)

  db = getDB()
  query = db.cursor()
  sql = '''
    DELETE FROM badge_wishlists WHERE user_discord_id = %s AND badge_filename = %s
  '''
  query.executemany(sql, badges_values_list)
  db.commit()
  query.close()
  db.close()

def db_clear_users_wishlist(user_discord_id):
  db = getDB()
  query = db.cursor()
  sql = '''
    DELETE FROM badge_wishlists WHERE user_discord_id = %s
  '''
  vals = (user_discord_id, )
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()

# .____                  __         /\  ____ ___      .__                 __
# |    |    ____   ____ |  | __    / / |    |   \____ |  |   ____   ____ |  | __
# |    |   /  _ \_/ ___\|  |/ /   / /  |    |   /    \|  |  /  _ \_/ ___\|  |/ /
# |    |__(  <_> )  \___|    <   / /   |    |  /   |  \  |_(  <_> )  \___|    <
# |_______ \____/ \___  >__|_ \ / /    |______/|___|  /____/\____/ \___  >__|_ \
#         \/          \/     \/ \/                  \/                 \/     \/
def db_autolock_badges_by_filenames_if_in_wishlist(user_discord_id, badge_filenames):
  badges_values_list = []
  for b in badge_filenames:
    tuple = (user_discord_id, b)
    badges_values_list.append(tuple)

  db = getDB()
  query = db.cursor()
  sql = '''
    UPDATE badges AS b
      JOIN badge_wishlists AS b_w
        ON b.user_discord_id = b_w.user_discord_id AND b.badge_filename = b_w.badge_filename
        SET b.locked = 1 WHERE b.user_discord_id = %s AND b.badge_filename = %s
  '''
  query.executemany(sql, badges_values_list)
  db.commit()
  query.close()
  db.close()

def db_get_badge_locked_status_by_name(user_discord_id, badge_name):
  db = getDB()
  query = db.cursor(dictionary=True, buffered=True)
  sql = '''
    SELECT b_i.*, b.locked FROM badge_info AS b_i
      JOIN badges AS b
        ON b_i.badge_filename = b.badge_filename
      WHERE b.user_discord_id = %s AND b_i.badge_name = %s
  '''
  vals = (user_discord_id, badge_name)
  query.execute(sql, vals)
  results = query.fetchone()
  query.close()
  db.close()
  return results

def db_lock_badge_by_filename(user_discord_id, badge_filename):
  db = getDB()
  query = db.cursor()
  sql = "UPDATE badges SET locked = 1 WHERE user_discord_id = %s AND badge_filename = %s"
  vals = (user_discord_id, badge_filename)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()

def db_lock_badges_by_filenames(user_discord_id, badge_filenames):
  badges_values_list = []
  for b in badge_filenames:
    tuple = (user_discord_id, b)
    badges_values_list.append(tuple)

  db = getDB()
  query = db.cursor()
  sql = '''
    UPDATE badges SET locked = 1 WHERE user_discord_id = %s AND badge_filename = %s
  '''
  query.executemany(sql, badges_values_list)
  db.commit()
  query.close()
  db.close()

def db_unlock_badge_by_filename(user_discord_id, badge_filename):
  db = getDB()
  query = db.cursor()
  sql = "UPDATE badges SET locked = 0 WHERE user_discord_id = %s AND badge_filename = %s"
  vals = (user_discord_id, badge_filename)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()

def db_unlock_badges_by_filenames(user_discord_id, badge_filenames):
  badges_values_list = []
  for b in badge_filenames:
    tuple = (user_discord_id, b)
    badges_values_list.append(tuple)

  db = getDB()
  query = db.cursor()
  sql = '''
    UPDATE badges SET locked = 0 WHERE user_discord_id = %s AND badge_filename = %s
  '''
  query.executemany(sql, badges_values_list)
  db.commit()
  query.close()
  db.close()


#    _____          __         .__
#   /     \ _____ _/  |_  ____ |  |__   ____   ______
#  /  \ /  \\__  \\   __\/ ___\|  |  \_/ __ \ /  ___/
# /    Y    \/ __ \|  | \  \___|   Y  \  ___/ \___ \
# \____|__  (____  /__|  \___  >___|  /\___  >____  >
#         \/     \/          \/     \/     \/     \/
def db_get_wishlist_matches(user_discord_id):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT b_i.badge_name, b.user_discord_id FROM badge_info AS b_i
      JOIN badges AS b
        ON b_i.badge_filename = b.badge_filename
      WHERE b.badge_filename IN (
        SELECT badge_filename FROM badge_wishlists WHERE user_discord_id = %s
      ) AND NOT b.locked
  '''
  vals = (user_discord_id, )
  query.execute(sql, vals)
  results = query.fetchall()
  query.close()
  db.close()
  return results

def db_get_wishlist_badge_matches(badge_filename):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT badge_filename, user_discord_id FROM badge_wishlists where badge_filename = %s
  '''
  vals = (badge_filename,)
  query.execute(sql, vals)
  results = query.fetchall()
  query.close()
  db.close()
  return results

def db_get_wishlist_inventory_matches(user_discord_id):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT b_i.badge_name, b_w.user_discord_id FROM badge_info AS b_i
      JOIN badge_wishlists AS b_w
        ON b_w.badge_filename = b_i.badge_filename
      JOIN badges AS b
        ON b.badge_filename = b_i.badge_filename
      WHERE b.user_discord_id = %s AND NOT b.locked
  '''
  vals = (user_discord_id, )
  query.execute(sql, vals)
  results = query.fetchall()
  query.close()
  db.close()
  return results