from common import *

#   ________        __
#  /  _____/  _____/  |_
# /   \  ____/ __ \   __\
# \    \_\  \  ___/|  |
#  \______  /\___  >__|
#         \/     \/
def db_get_user_wishlist_badges(user_discord_id):
  with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT * FROM badge_info AS b_i
        JOIN badge_wishlists AS b_w
        ON b_w.user_discord_id = %s AND b_i.badge_filename = b_w.badge_filename
        ORDER BY b_i.badge_name ASC
    '''
    vals = (user_discord_id,)
    query.execute(sql, vals)
    badges = query.fetchall()
  return badges


#    _____       .___  .___     /\ __________
#   /  _  \    __| _/__| _/    / / \______   \ ____   _____   _______  __ ____
#  /  /_\  \  / __ |/ __ |    / /   |       _// __ \ /     \ /  _ \  \/ // __ \
# /    |    \/ /_/ / /_/ |   / /    |    |   \  ___/|  Y Y  (  <_> )   /\  ___/
# \____|__  /\____ \____ |  / /     |____|_  /\___  >__|_|  /\____/ \_/  \___  >
#         \/      \/    \/  \/             \/     \/      \/                 \/
def db_add_badge_name_to_users_wishlist(user_discord_id, badge_name):
  with AgimusDB() as query:
    sql = '''
      INSERT INTO badge_wishlists (user_discord_id, badge_filename)
        VALUES (%s, (SELECT badge_filename FROM badge_info WHERE badge_name = %s))
    '''
    vals = (user_discord_id, badge_name)
    query.execute(sql, vals)

def db_add_badge_filenames_to_users_wishlist(user_discord_id, badge_filenames):
  badges_values_list = []
  for b in badge_filenames:
    tuple = (user_discord_id, b)
    badges_values_list.append(tuple)

  with AgimusDB() as query:
    sql = '''
      INSERT INTO badge_wishlists (user_discord_id, badge_filename)
        VALUES (%s, %s)
    '''
    query.executemany(sql, badges_values_list)

def db_remove_badge_name_from_users_wishlist(user_discord_id, badge_name):
  with AgimusDB() as query:
    sql = '''
      DELETE b_w FROM badge_wishlists AS b_w
        JOIN badge_info AS b_i
          ON b_w.badge_filename = b_i.badge_filename
        WHERE b_w.user_discord_id = %s AND b_i.badge_name = %s
    '''
    vals = (user_discord_id, badge_name)
    query.execute(sql, vals)

def db_remove_badge_filenames_from_users_wishlist(user_discord_id, badge_filenames):
  badges_values_list = []
  for b in badge_filenames:
    tuple = (user_discord_id, b)
    badges_values_list.append(tuple)

  with AgimusDB() as query:
    sql = '''
      DELETE FROM badge_wishlists WHERE user_discord_id = %s AND badge_filename = %s
    '''
    query.executemany(sql, badges_values_list)

def db_clear_users_wishlist(user_discord_id):
  with AgimusDB() as query:
    sql = '''
      DELETE FROM badge_wishlists WHERE user_discord_id = %s
    '''
    vals = (user_discord_id, )
    query.execute(sql, vals)


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

  with AgimusDB() as query:
    sql = '''
      UPDATE badges AS b
        JOIN badge_wishlists AS b_w
          ON b.user_discord_id = b_w.user_discord_id AND b.badge_filename = b_w.badge_filename
          SET b.locked = 1 WHERE b.user_discord_id = %s AND b.badge_filename = %s
    '''
    query.executemany(sql, badges_values_list)

def db_get_badge_locked_status_by_name(user_discord_id, badge_name):
  with AgimusDB(dictionary=True, buffered=True) as query:
    sql = '''
      SELECT b_i.*, b.locked FROM badge_info AS b_i
        JOIN badges AS b
          ON b_i.badge_filename = b.badge_filename
        WHERE b.user_discord_id = %s AND b_i.badge_name = %s
    '''
    vals = (user_discord_id, badge_name)
    query.execute(sql, vals)
    results = query.fetchone()
  return results

def db_lock_badge_by_filename(user_discord_id, badge_filename):
  with AgimusDB() as query:
    sql = "UPDATE badges SET locked = 1 WHERE user_discord_id = %s AND badge_filename = %s"
    vals = (user_discord_id, badge_filename)
    query.execute(sql, vals)

def db_lock_badges_by_filenames(user_discord_id, badge_filenames):
  badges_values_list = []
  for b in badge_filenames:
    tuple = (user_discord_id, b)
    badges_values_list.append(tuple)

  with AgimusDB() as query:
    sql = '''
      UPDATE badges SET locked = 1 WHERE user_discord_id = %s AND badge_filename = %s
    '''
    query.executemany(sql, badges_values_list)

def db_unlock_badge_by_filename(user_discord_id, badge_filename):
  with AgimusDB() as query:
    sql = "UPDATE badges SET locked = 0 WHERE user_discord_id = %s AND badge_filename = %s"
    vals = (user_discord_id, badge_filename)
    query.execute(sql, vals)

def db_unlock_badges_by_filenames(user_discord_id, badge_filenames):
  badges_values_list = []
  for b in badge_filenames:
    tuple = (user_discord_id, b)
    badges_values_list.append(tuple)

  with AgimusDB() as query:
    sql = '''
      UPDATE badges SET locked = 0 WHERE user_discord_id = %s AND badge_filename = %s
    '''
    query.executemany(sql, badges_values_list)


#    _____          __         .__
#   /     \ _____ _/  |_  ____ |  |__   ____   ______
#  /  \ /  \\__  \\   __\/ ___\|  |  \_/ __ \ /  ___/
# /    Y    \/ __ \|  | \  \___|   Y  \  ___/ \___ \
# \____|__  (____  /__|  \___  >___|  /\___  >____  >
#         \/     \/          \/     \/     \/     \/
def db_get_wishlist_matches(user_discord_id):
  with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT b_i.*, b.user_discord_id FROM badge_info AS b_i
        JOIN badges AS b
          ON b_i.badge_filename = b.badge_filename
        WHERE b.badge_filename IN (
          SELECT badge_filename FROM badge_wishlists WHERE user_discord_id = %s
        ) AND NOT b.locked
    '''
    vals = (user_discord_id, )
    query.execute(sql, vals)
    results = query.fetchall()
  return results

def db_get_wishlist_badge_matches(badge_filename):
  with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT badge_filename, user_discord_id FROM badge_wishlists where badge_filename = %s
    '''
    vals = (badge_filename,)
    query.execute(sql, vals)
    results = query.fetchall()
  return results

def db_get_wishlist_inventory_matches(user_discord_id):
  with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT b_i.*, b_w.user_discord_id FROM badge_info AS b_i
        JOIN badge_wishlists AS b_w
          ON b_w.badge_filename = b_i.badge_filename
        JOIN badges AS b
          ON b.badge_filename = b_i.badge_filename
        WHERE b.user_discord_id = %s AND NOT b.locked
    '''
    vals = (user_discord_id, )
    query.execute(sql, vals)
    results = query.fetchall()
  return results


# ________  .__               .__                      .__
# \______ \ |__| ______ _____ |__| ______ ___________  |  |   ______
#  |    |  \|  |/  ___//     \|  |/  ___//  ___/\__  \ |  |  /  ___/
#  |    `   \  |\___ \|  Y Y  \  |\___ \ \___ \  / __ \|  |__\___ \
# /_______  /__/____  >__|_|  /__/____  >____  >(____  /____/____  >
#         \/        \/      \/        \/     \/      \/          \/
def db_get_wishlist_dismissal(user_discord_id, match_discord_id):
  with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT * FROM wishlist_dismissals WHERE user_discord_id = %s AND match_discord_id = %s;
    '''
    vals = (user_discord_id, match_discord_id)
    query.execute(sql, vals)
    results = query.fetchone()
  return results

def db_delete_wishlist_dismissal(user_discord_id, match_discord_id):
  with AgimusDB(dictionary=True) as query:
    sql = '''
      DELETE FROM wishlist_dismissals WHERE user_discord_id = %s AND match_discord_id = %s;
    '''
    vals = (user_discord_id, match_discord_id)
    query.execute(sql, vals)

def db_add_wishlist_dismissal(user_discord_id, match_discord_id, has, wants):
  with AgimusDB() as query:
    sql = '''
      INSERT INTO wishlist_dismissals (user_discord_id, match_discord_id, has, wants)
        VALUES (%s, %s, %s, %s)
    '''
    vals = (user_discord_id, match_discord_id, has, wants)
    query.execute(sql, vals)
