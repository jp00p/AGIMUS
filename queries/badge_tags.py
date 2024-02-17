from common import *

# ________                      .__
# \_____  \  __ __   ___________|__| ____   ______
#  /  / \  \|  |  \_/ __ \_  __ \  |/ __ \ /  ___/
# /   \_/.  \  |  /\  ___/|  | \/  \  ___/ \___ \
# \_____\ \_/____/  \___  >__|  |__|\___  >____  >
#        \__>           \/              \/     \/

def db_get_user_badge_tags(user_discord_id) -> list:
  """
  returns a list of the users's current custom badge tags
  """
  with AgimusDB(dictionary=True) as query:
    sql = "SELECT * FROM badge_tags WHERE user_discord_id = %s ORDER BY tag_name ASC"
    vals = (user_discord_id,)
    query.execute(sql, vals)
    results = query.fetchall()
  return results


def db_create_user_tag(user_discord_id, tag) -> None:
  """
  creates a new tag for the user in question
  """
  with AgimusDB() as query:
    sql = "INSERT INTO badge_tags (user_discord_id, tag_name) VALUES (%s, %s)"
    vals = (user_discord_id, tag)
    query.execute(sql, vals)

def db_delete_user_tag(user_discord_id, tag) -> None:
  """
  delete a tag for the user in question
  """
  with AgimusDB() as query:
    sql = "DELETE FROM badge_tags WHERE user_discord_id = %s AND tag_name = %s"
    vals = (user_discord_id, tag)
    query.execute(sql, vals)

def db_rename_user_tag(user_discord_id, tag, new_name) -> None:
  """
  renames a tag for the user in question
  """
  with AgimusDB() as query:
    sql = "UPDATE badge_tags SET tag_name = %s WHERE user_discord_id = %s AND tag_name = %s"
    vals = (new_name, user_discord_id, tag)
    query.execute(sql, vals)

def db_get_associated_badge_tags(user_discord_id, badge_filename) -> list:
  """
  returns a list of the current tags the user has associated with a given badge
  """
  with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT b_t.* FROM badge_tags AS b_t
        JOIN badge_tags_associations AS t_a ON b_t.id = t_a.badge_tags_id
        JOIN badges AS b ON t_a.badges_id = b.id
        JOIN badge_info AS b_i ON b_i.badge_filename = b.badge_filename
          WHERE b_i.badge_filename = %s AND b_t.user_discord_id = %s
    '''
    vals = (badge_filename, user_discord_id)
    query.execute(sql, vals)
    results = query.fetchall()
  return results


def db_create_badge_tags_associations(user_discord_id, badge_filename, tag_ids):
  """
  associates a list of tags with a user's specific badge
  """
  tags_values_list = []
  for id in tag_ids:
    tuple = (id, badge_filename, user_discord_id)
    tags_values_list.append(tuple)

  with AgimusDB(dictionary=True) as query:
    sql = '''
      INSERT INTO badge_tags_associations (badges_id, badge_tags_id)
        SELECT b.id, %s
          FROM badges AS b
          JOIN badge_info AS b_i ON b_i.badge_filename = b.badge_filename
            WHERE b_i.badge_filename = %s AND b.user_discord_id = %s
    '''
    query.executemany(sql, tags_values_list)

def db_delete_badge_tags_associations(tag_ids, badge_filename):
  """
  deletes a list of tags from association with a user's specific badge
  """
  tags_values_list = []
  for id in tag_ids:
    tuple = (id, badge_filename)
    tags_values_list.append(tuple)

  with AgimusDB(dictionary=True) as query:
    sql = '''
      DELETE t_a FROM badge_tags_associations AS t_a
        JOIN badges AS b ON b.id = t_a.badges_id
          WHERE t_a.badge_tags_id = %s AND b.badge_filename = %s
    '''
    query.executemany(sql, tags_values_list)

def db_get_user_tagged_badges(user_discord_id, tag):
  '''
    get_user_badges(user_discord_id)
    user_discord_id[required]: int
    returns a list of badges the user has
  '''
  with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT b_i.badge_name, b_i.badge_filename, b.locked, b_i.special FROM badges b
        JOIN badge_info AS b_i
          ON b.badge_filename = b_i.badge_filename
        JOIN badge_tags_associations AS t_a
          ON t_a.badges_id = b.id
        JOIN badge_tags AS b_t
          ON b.user_discord_id = b_t.user_discord_id AND t_a.badge_tags_id = b_t.id
        WHERE b.user_discord_id = %s AND b_t.tag_name = %s
          ORDER BY b_i.badge_filename ASC
    '''
    vals = (user_discord_id, tag)
    query.execute(sql, vals)
    badges = query.fetchall()
  return badges

def db_get_last_tagged_badge_filename(user_discord_id):
  with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT badge_filename FROM tags_carousel_position WHERE user_discord_id = %s LIMIT 1;
    '''
    vals = (user_discord_id,)
    query.execute(sql, vals)
    results = query.fetchone()
  if results:
    return results['badge_filename']
  else:
    return None

def db_upsert_last_tagged_badge_filename(user_discord_id, badge_filename):
  """
  either creates or modifies the user's tags_carousel_position row
  with the given badge_filename to indicate the last badge they've tagged
  """
  with AgimusDB() as query:
    sql = '''
      INSERT INTO tags_carousel_position
        (user_discord_id, badge_filename)
      VALUES
        (%s, %s)
      ON DUPLICATE KEY UPDATE
        badge_filename = %s
    '''
    vals = (user_discord_id, badge_filename, badge_filename)
    query.execute(sql, vals)

def db_clear_last_tagged_badge_filename(user_discord_id):
  """
  deletes the user's record from the tags_carousel_position table
  so that the next time they load the interface they'll start at the front again
  """
  with AgimusDB() as query:
    sql = '''
      DELETE FROM tags_carousel_position WHERE user_discord_id = %s
    '''
    vals = (user_discord_id,)
    query.execute(sql, vals)