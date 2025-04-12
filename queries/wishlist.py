from common import *

#   ________        __
#  /  _____/  _____/  |_
# /   \  ____/ __ \   __\
# \    \_\  \  ___/|  |
#  \______  /\___  >__|
#         \/     \/
async def db_get_user_wishlist_badge_info_records(user_discord_id):
  """
  Retrieve all badge_info records that a user has wishlisted.
  Joins badge_instance_wishlists with badge_info to return badge metadata.
  Results are ordered alphabetically by badge name.
  """
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT * FROM badge_info AS b_i
        JOIN badge_instance_wishlists AS b_w
        ON b_w.badge_info_id = b_i.id
        WHERE b_w.user_discord_id = %s
        ORDER BY b_i.badge_name ASC
    '''
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    return await query.fetchall()

#    _____       .___  .___     /\ __________
#   /  _  \    __| _/__| _/    / / \______   \ ____   _____   _______  __ ____
#  /  /_\  \  / __ |/ __ |    / /   |       _// __ \ /     \ /  _ \  \/ // __ \
# /    |    \/ /_/ / /_/ |   / /    |    |   \  ___/|  Y Y  (  <_> )   /\  ___/
# \____|__  /\____ \____ |  / /     |____|_  /\___  >__|_|  /\____/ \_/  \___  >
#         \/      \/    \/  \/             \/     \/      \/                 \/
async def db_add_badge_name_to_users_wishlist(user_discord_id, badge_name):
  """
  Add a badge to the user's wishlist using the badge's name.
  Resolves the badge_info_id via a subquery on badge_info.
  """
  async with AgimusDB() as query:
    sql = '''
      INSERT INTO badge_instance_wishlists (user_discord_id, badge_info_id)
        VALUES (%s, (SELECT id FROM badge_info WHERE badge_name = %s))
    '''
    vals = (user_discord_id, badge_name)
    await query.execute(sql, vals)

async def db_add_badge_info_ids_to_users_wishlist(user_discord_id, badge_info_ids):
  """
  Add multiple badge_info_id entries to a user's wishlist.
  Uses INSERT IGNORE to avoid duplicate constraints.
  """
  values = [(user_discord_id, badge_info_id) for badge_info_id in badge_info_ids]
  async with AgimusDB() as query:
    sql = '''
      INSERT IGNORE INTO badge_instance_wishlists (user_discord_id, badge_info_id)
        VALUES (%s, %s)
    '''
    await query.executemany(sql, values)

async def db_remove_badge_name_from_users_wishlist(user_discord_id, badge_name):
  """
  Remove a badge from the user's wishlist by badge name.
  Resolves badge_info_id via a join on badge_info.
  """
  async with AgimusDB() as query:
    sql = '''
      DELETE b_w FROM badge_instance_wishlists AS b_w
        JOIN badge_info AS b_i ON b_w.badge_info_id = b_i.id
        WHERE b_w.user_discord_id = %s AND b_i.badge_name = %s
    '''
    vals = (user_discord_id, badge_name)
    await query.execute(sql, vals)

async def db_remove_badge_info_ids_from_users_wishlist(user_discord_id, badge_info_ids):
  """
  Remove multiple badges from a user's wishlist by badge_info_id.
  """
  values = [(user_discord_id, badge_info_id) for badge_info_id in badge_info_ids]
  async with AgimusDB() as query:
    sql = '''
      DELETE FROM badge_instance_wishlists WHERE user_discord_id = %s AND badge_info_id = %s
    '''
    await query.executemany(sql, values)

async def db_clear_users_wishlist(user_discord_id):
  """
  Delete all entries in the wishlist for the given user.
  """
  async with AgimusDB() as query:
    sql = '''
      DELETE FROM badge_instance_wishlists WHERE user_discord_id = %s
    '''
    vals = (user_discord_id, )
    await query.execute(sql, vals)

async def db_purge_users_wishlist(user_discord_id):
  """
  Remove wishlist entries for badges that the user already owns.
  Cross-references badge_instances to perform the cleanup.
  """
  async with AgimusDB() as query:
    sql = '''
      DELETE b_w FROM badge_instance_wishlists AS b_w
        JOIN badge_instances AS b_inst
          ON b_inst.badge_info_id = b_w.badge_info_id AND b_inst.owner_discord_id = b_w.user_discord_id
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
async def db_get_user_wishlist_badge_info_records(user_discord_id):
  """
  Retrieve all badge_info records that a user has wishlisted.
  Joins badge_instance_wishlists with badge_info to return badge metadata.
  Results are ordered alphabetically by badge name.
  """
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT * FROM badge_info AS b_i
        JOIN badge_instance_wishlists AS b_w
        ON b_w.badge_info_id = b_i.id
        WHERE b_w.user_discord_id = %s
        ORDER BY b_i.badge_name ASC
    '''
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    return await query.fetchall()

async def db_autolock_badges_by_filenames_if_in_wishlist(user_discord_id, badge_filenames):
  """
  Lock badge instances from the user's inventory if they appear in their wishlist.
  Uses badge_filenames to map into badge_info and cross-reference against wishlist.
  """
  values = [(user_discord_id, b) for b in badge_filenames]
  async with AgimusDB() as query:
    sql = '''
      UPDATE badge_instances AS b
        JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
        JOIN badge_instance_wishlists AS biw
          ON biw.user_discord_id = b.owner_discord_id AND biw.badge_info_id = b_i.id
        SET b.locked = 1
        WHERE b.owner_discord_id = %s AND b_i.badge_filename = %s
    '''
    await query.executemany(sql, values)

async def db_get_badge_locked_status_by_name(user_discord_id, badge_name):
  """
  Return the badge_info record and lock status for a given badge_name owned by the user.
  """
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT b_i.*, b.locked AS locked FROM badge_info AS b_i
        JOIN badge_instances AS b ON b.badge_info_id = b_i.id
        WHERE b.owner_discord_id = %s AND b_i.badge_name = %s
    '''
    vals = (user_discord_id, badge_name)
    await query.execute(sql, vals)
    return await query.fetchone()

async def db_lock_badge_by_filename(user_discord_id, badge_filename):
  """
  Lock a specific badge instance owned by the user using the badge's filename.
  """
  async with AgimusDB() as query:
    sql = '''
      UPDATE badge_instances AS b
        JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
        SET b.locked = 1
        WHERE b.owner_discord_id = %s AND b_i.badge_filename = %s
    '''
    await query.execute(sql, (user_discord_id, badge_filename))

async def db_lock_badges_by_filenames(user_discord_id, badge_filenames):
  """
  Lock multiple badge instances owned by the user using badge filenames.
  """
  values = [(user_discord_id, b) for b in badge_filenames]
  async with AgimusDB() as query:
    sql = '''
      UPDATE badge_instances AS b
        JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
        SET b.locked = 1
        WHERE b.owner_discord_id = %s AND b_i.badge_filename = %s
    '''
    await query.executemany(sql, values)

async def db_unlock_badge_by_filename(user_discord_id, badge_filename):
  """
  Unlock a specific badge instance owned by the user using the badge's filename.
  """
  async with AgimusDB() as query:
    sql = '''
      UPDATE badge_instances AS b
        JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
        SET b.locked = 0
        WHERE b.owner_discord_id = %s AND b_i.badge_filename = %s
    '''
    await query.execute(sql, (user_discord_id, badge_filename))

async def db_unlock_badges_by_filenames(user_discord_id, badge_filenames):
  """
  Unlock multiple badge instances owned by the user using badge filenames.
  """
  values = [(user_discord_id, b) for b in badge_filenames]
  async with AgimusDB() as query:
    sql = '''
      UPDATE badge_instances AS b
        JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
        SET b.locked = 0
        WHERE b.owner_discord_id = %s AND b_i.badge_filename = %s
    '''
    await query.executemany(sql, values)

#    _____          __         .__
#   /     \ _____ _/  |_  ____ |  |__   ____   ______
#  /  \ /  \\__  \\   __\/ ___\|  |  \_/ __ \ /  ___/
# /    Y    \/ __ \|  | \  \___|   Y  \  ___/ \___ \
# \____|__  (____  /__|  \___  >___|  /\___  >____  >
#         \/     \/          \/     \/     \/     \/
async def db_get_wishlist_matches(user_discord_id):
  """
  Return a list of badge instances that match the user's wishlist.
  Joins badge_instances with badge_info and filters on wishlist entries.
  Only unlocked instances are returned.
  """
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT b_i.*, b.owner_discord_id AS user_discord_id FROM badge_info AS b_i
        JOIN badge_instances AS b ON b.badge_info_id = b_i.id
        WHERE b_i.id IN (
          SELECT badge_info_id FROM badge_instance_wishlists WHERE user_discord_id = %s
        ) AND NOT b.locked
    '''
    await query.execute(sql, (user_discord_id,))
    return await query.fetchall()

async def db_get_wishlist_badge_matches(badge_info_id):
  """
  Return all wishlist entries (user ids) that include the given badge_info_id.
  """
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT user_discord_id, badge_info_id FROM badge_instance_wishlists
      WHERE badge_info_id = %s
    '''
    vals = (badge_info_id,)
    await query.execute(sql, vals)
    return await query.fetchall()

async def db_get_wishlist_inventory_matches(user_discord_id):
  """
  Return all badges that the user owns that are present in other users' wishlists.
  Filters out locked badge instances.
  """
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT b_i.*, biw.user_discord_id FROM badge_info AS b_i
        JOIN badge_instance_wishlists AS biw ON biw.badge_info_id = b_i.id
        JOIN badge_instances AS b ON b.badge_info_id = b_i.id
        WHERE b.owner_discord_id = %s AND NOT b.locked
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
  """
  Fetch a single wishlist dismissal entry for a given user and match.
  Returns None if not found.
  """
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT * FROM badge_instance_wishlist_dismissals WHERE user_discord_id = %s AND match_discord_id = %s LIMIT 1
    '''
    vals = (user_discord_id, match_discord_id)
    await query.execute(sql, vals)
    return await query.fetchone()

async def db_get_all_users_wishlist_dismissals(user_discord_id):
  """
  Fetch all wishlist dismissal records for the given user.
  """
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT * FROM badge_instance_wishlist_dismissals WHERE user_discord_id = %s
    '''
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    return await query.fetchall()

async def db_delete_wishlist_dismissal(user_discord_id, match_discord_id):
  """
  Delete a specific wishlist dismissal record for a user and matched user.
  """
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      DELETE FROM badge_instance_wishlist_dismissals WHERE user_discord_id = %s AND match_discord_id = %s
    '''
    vals = (user_discord_id, match_discord_id)
    await query.execute(sql, vals)

async def db_add_wishlist_dismissal(user_discord_id, match_discord_id, has, wants):
  """
  Add a wishlist dismissal record.
  `has` and `wants` should be serialized JSON arrays of badge names.
  """
  async with AgimusDB() as query:
    sql = '''
      INSERT INTO badge_instance_wishlist_dismissals (user_discord_id, match_discord_id, has, wants)
      VALUES (%s, %s, %s, %s)
    '''
    vals = (user_discord_id, match_discord_id, has, wants)
    await query.execute(sql, vals)

