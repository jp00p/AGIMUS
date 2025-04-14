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

async def db_get_associated_user_badge_tags_by_instance_id(user_discord_id, badge_instance_id) -> list:
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT b_t.*
      FROM badge_tags AS b_t
      JOIN badge_instances_tags_associations AS t_a ON b_t.id = t_a.badge_tags_id
      JOIN badge_instances AS inst ON t_a.badge_instance_id = inst.id
      WHERE b_t.user_discord_id = %s AND inst.id = %s
        AND inst.active = TRUE
    '''
    vals = (user_discord_id, badge_instance_id)
    await query.execute(sql, vals)
    return await query.fetchall()

async def db_create_user_badge_instances_tags_associations(user_discord_id, badge_instance_id, tag_ids):
  async with AgimusDB(dictionary=True) as query:
    # Validate ownership before inserting
    await query.execute(
      '''
        SELECT id FROM badge_instances
        WHERE id = %s AND owner_discord_id = %s AND active = TRUE
      ''',
      (badge_instance_id, user_discord_id)
    )
    instance = await query.fetchone()
    if not instance:
      return  # Skip if badge_instance does not belong to user

  # Safe to insert associations
  async with AgimusDB() as query:
    await query.executemany(
      '''
        INSERT IGNORE INTO badge_instances_tags_associations (badge_instance_id, badge_tags_id)
        VALUES (%s, %s)
      ''',
      [(badge_instance_id, tag_id) for tag_id in tag_ids]
    )

async def db_delete_user_badge_instances_tags_associations(user_discord_id, tag_ids, badge_instance_id):
  async with AgimusDB() as query:
    await query.executemany(
      '''
        DELETE t_a
        FROM badge_instances_tags_associations AS t_a
        JOIN badge_instances AS inst ON inst.id = t_a.badge_instance_id
        WHERE t_a.badge_tags_id = %s
          AND t_a.badge_instance_id = %s
          AND inst.owner_discord_id = %s
          AND inst.active = TRUE
      ''',
      [(tag_id, badge_instance_id, user_discord_id) for tag_id in tag_ids]
    )

async def db_get_user_tagged_badges(user_discord_id, tag):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT
        inst.id AS badge_instance_id,
        info.id AS badge_info_id,
        info.badge_name,
        info.badge_filename,
        inst.locked,
        info.special
      FROM badge_tags AS tags
      JOIN badge_instances_tags_associations AS assoc ON tags.id = assoc.badge_tags_id
      JOIN badge_instances AS inst ON assoc.badge_instance_id = inst.id
      JOIN badge_info AS info ON inst.badge_info_id = info.id
      WHERE tags.user_discord_id = %s
        AND tags.tag_name = %s
        AND inst.active = TRUE
      ORDER BY info.badge_filename ASC
    '''
    await query.execute(sql, (user_discord_id, tag))
    return await query.fetchall()


async def db_get_last_carousel_tagged_badge_instance(user_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT
        inst.id AS badge_instance_id,
        info.id AS badge_info_id,
        info.badge_name,
        info.badge_filename,
        inst.locked,
        info.special
      FROM badge_instances_tags_carousel_position AS cp
      JOIN badge_instances AS inst ON cp.badge_instance_id = inst.id
      JOIN badge_info AS info ON inst.badge_info_id = info.id
      WHERE cp.user_discord_id = %s AND inst.active = TRUE
      ORDER BY info.badge_filename ASC
      LIMIT 1
    '''
    await query.execute(sql, (user_discord_id,))
    row = await query.fetchone()
  return row


async def db_upsert_last_carousel_tagged_badge_instance(user_discord_id, badge_instance_id):
  async with AgimusDB() as query:
    sql = '''
      INSERT INTO badge_instances_tags_carousel_position (user_discord_id, badge_instance_id)
      VALUES (%s, %s) as new
      ON DUPLICATE KEY UPDATE
        badge_instance_id = new.badge_instance_id,
        last_modified = CURRENT_TIMESTAMP
    '''
    await query.execute(sql, (user_discord_id, badge_instance_id))


async def db_clear_last_carousel_tagged_badge_instance(user_discord_id):
  async with AgimusDB() as query:
    sql = '''
      DELETE FROM badge_instances_tags_carousel_position
      WHERE user_discord_id = %s
    '''
    await query.execute(sql, (user_discord_id,))
