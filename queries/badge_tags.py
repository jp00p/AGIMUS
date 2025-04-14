from common import *

# ________                      .__
# \_____  \  __ __   ___________|__| ____   ______
#  /  / \  \|  |  \_/ __ \_  __ \  |/ __ \ /  ___/
# /   \_/.  \  |  /\  ___/|  | \/  \  ___/ \___ \
# \_____\ \_/____/  \___  >__|  |__|\___  >____  >
#        \__>           \/              \/     \/

async def db_get_user_badge_tags(user_discord_id) -> list:
  """
  returns a list of the users's current custom badge tags
  """
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT * FROM badge_tags WHERE user_discord_id = %s ORDER BY tag_name ASC"
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    results = await query.fetchall()
  return results


async def db_create_user_badge_tag(user_discord_id, tag) -> None:
  """
  creates a new badge tag for the user in question
  """
  async with AgimusDB() as query:
    sql = "INSERT INTO badge_tags (user_discord_id, tag_name) VALUES (%s, %s)"
    vals = (user_discord_id, tag)
    await query.execute(sql, vals)

async def db_delete_user_badge_tag(user_discord_id, tag) -> None:
  """
  delete a badge tag for the user in question
  """
  async with AgimusDB() as query:
    sql = "DELETE FROM badge_tags WHERE user_discord_id = %s AND tag_name = %s"
    vals = (user_discord_id, tag)
    await query.execute(sql, vals)

async def db_rename_user_badge_tag(user_discord_id, tag, new_name) -> None:
  """
  renames a tag for the user in question
  """
  async with AgimusDB() as query:
    sql = "UPDATE badge_tags SET tag_name = %s WHERE user_discord_id = %s AND tag_name = %s"
    vals = (new_name, user_discord_id, tag)
    await query.execute(sql, vals)

async def db_get_associated_user_badge_tags_by_filename(user_discord_id, badge_filename) -> list:
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT b_t.*
      FROM badge_tags AS b_t
      JOIN badge_tags_associations AS t_a ON b_t.id = t_a.badge_tags_id
      JOIN badge_instances AS inst ON t_a.badge_instance_id = inst.id
      JOIN badge_info AS info ON inst.badge_info_id = info.id
      WHERE b_t.user_discord_id = %s AND info.badge_filename = %s
        AND inst.status = 'active'
    '''
    vals = (user_discord_id, badge_filename)
    await query.execute(sql, vals)
    return await query.fetchall()

async def db_create_user_badge_tags_associations(user_discord_id, badge_filename, tag_ids):
  values = []

  async with AgimusDB(dictionary=True) as query:
    # Get instance ID
    await query.execute(
      '''
        SELECT inst.id
        FROM badge_instances AS inst
        JOIN badge_info AS info ON inst.badge_info_id = info.id
        WHERE info.badge_filename = %s
          AND inst.owner_discord_id = %s
          AND inst.status = 'active'
        LIMIT 1
      ''',
      (badge_filename, user_discord_id)
    )
    row = await query.fetchone()
    if not row:
      return  # No valid badge instance found

    instance_id = row['id']
    values = [(instance_id, tag_id) for tag_id in tag_ids]

  async with AgimusDB() as query:
    await query.executemany(
      '''
        INSERT IGNORE INTO badge_tags_associations (badge_instance_id, badge_tags_id)
        VALUES (%s, %s)
      ''',
      values
    )

async def db_delete_badge_tags_associations(tag_ids, badge_filename):
  async with AgimusDB(dictionary=True) as query:
    await query.execute(
      '''
        SELECT inst.id
        FROM badge_instances AS inst
        JOIN badge_info AS info ON inst.badge_info_id = info.id
        WHERE info.badge_filename = %s
          AND inst.status = 'active'
        LIMIT 1
      ''',
      (badge_filename,)
    )
    row = await query.fetchone()
    if not row:
      return

    instance_id = row['id']
    values = [(tag_id, instance_id) for tag_id in tag_ids]

  async with AgimusDB() as query:
    await query.executemany(
      '''
        DELETE FROM badge_tags_associations
        WHERE badge_tags_id = %s AND badge_instance_id = %s
      ''',
      values
    )

async def db_get_user_tagged_badges(user_discord_id, tag):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT
        info.badge_name,
        info.badge_filename,
        inst.locked,
        info.special
      FROM badge_tags AS tags
      JOIN badge_tags_associations AS assoc ON tags.id = assoc.badge_tags_id
      JOIN badge_instances AS inst ON assoc.badge_instance_id = inst.id
      JOIN badge_info AS info ON inst.badge_info_id = info.id
      WHERE tags.user_discord_id = %s
        AND tags.tag_name = %s
        AND inst.status = 'active'
      ORDER BY info.badge_filename ASC
    '''
    await query.execute(sql, (user_discord_id, tag))
    return await query.fetchall()


async def db_get_last_carousel_tagged_badge_instance_id(user_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT badge_instance_id
      FROM tags_carousel_position
      WHERE user_discord_id = %s
      LIMIT 1
    '''
    await query.execute(sql, (user_discord_id,))
    row = await query.fetchone()
  return row['badge_instance_id'] if row else None


async def db_upsert_last_carousel_tagged_badge_instance_id(user_discord_id, badge_instance_id):
  async with AgimusDB() as query:
    sql = '''
      INSERT INTO tags_carousel_position (user_discord_id, badge_instance_id)
      VALUES (%s, %s)
      ON DUPLICATE KEY UPDATE
        badge_instance_id = VALUES(badge_instance_id),
        last_modified = CURRENT_TIMESTAMP
    '''
    await query.execute(sql, (user_discord_id, badge_instance_id))


async def db_clear_last_carousel_tagged_badge_instance(user_discord_id):
  async with AgimusDB() as query:
    sql = '''
      DELETE FROM tags_carousel_position
      WHERE user_discord_id = %s
    '''
    await query.execute(sql, (user_discord_id,))


# async def db_get_last_carousel_badge_instance_with_info(user_discord_id):
#   async with AgimusDB(dictionary=True) as query:
#     sql = '''
#       SELECT bi.*, inst.*
#       FROM tags_carousel_position AS tcp
#       JOIN badge_instances AS inst ON tcp.badge_instance_id = inst.id
#       JOIN badge_info AS bi ON inst.badge_info_id = bi.id
#       WHERE tcp.user_discord_id = %s
#     '''
#     await query.execute(sql, (user_discord_id,))
#     return await query.fetchone()
