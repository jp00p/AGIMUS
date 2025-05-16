from common import *

from utils.badge_instances import BADGE_INSTANCE_COLUMNS

# ________                      .__
# \_____  \  __ __   ___________|__| ____   ______
#  /  / \  \|  |  \_/ __ \_  __ \  |/ __ \ /  ___/
# /   \_/.  \  |  /\  ___/|  | \/  \  ___/ \___ \
# \_____\ \_/____/  \___  >__|  |__|\___  >____  >
#        \__>           \/              \/     \/

# Tags themselves
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

# Tags to `badge_info` Associations
async def db_get_associated_user_badge_tags_by_info_id(user_discord_id, badge_info_id) -> list:
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT t.*
      FROM badge_tags AS t
      JOIN badge_info_tags_associations AS a ON a.badge_tags_id = t.id
      WHERE a.user_discord_id = %s AND a.badge_info_id = %s
    '''
    await query.execute(sql, (user_discord_id, badge_info_id))
    return await query.fetchall()

async def db_create_user_badge_info_tags_associations(user_discord_id, badge_info_id, tag_ids):
  async with AgimusDB() as query:
    await query.executemany(
      '''
        INSERT IGNORE INTO badge_info_tags_associations (user_discord_id, badge_info_id, badge_tags_id)
        VALUES (%s, %s, %s)
      ''',
      [(user_discord_id, badge_info_id, tag_id) for tag_id in tag_ids]
    )

async def db_delete_user_badge_info_tags_associations(user_discord_id, tag_ids, badge_info_id):
  async with AgimusDB() as query:
    await query.executemany(
      '''
        DELETE FROM badge_info_tags_associations
        WHERE user_discord_id = %s AND badge_info_id = %s AND badge_tags_id = %s
      ''',
      [(user_discord_id, badge_info_id, tag_id) for tag_id in tag_ids]
    )

async def db_get_user_tagged_badge_instances_by_prestige(user_discord_id, tag_name, prestige_level):
  async with AgimusDB(dictionary=True) as query:
    sql = f"""
      SELECT {BADGE_INSTANCE_COLUMNS}
      FROM badge_instances AS b
      JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
      LEFT JOIN badge_crystals AS c ON b.active_crystal_id = c.id
      LEFT JOIN crystal_instances AS ci ON c.crystal_instance_id = ci.id
      LEFT JOIN crystal_types AS t ON ci.crystal_type_id = t.id
      JOIN badge_info_tags_associations AS assoc ON b.badge_info_id = assoc.badge_info_id
      JOIN badge_tags AS tag ON assoc.badge_tags_id = tag.id
      WHERE b.owner_discord_id = %s
        AND b.prestige_level = %s
        AND assoc.user_discord_id = %s
        AND tag.tag_name = %s
        AND b.active = TRUE
      ORDER BY b.badge_info_id
    """
    await query.execute(sql, (user_discord_id, prestige_level, user_discord_id, tag_name))
    return await query.fetchall()


# Carousel
async def db_get_last_carousel_badge_info(user_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT b.id AS badge_info_id, b.badge_name, b.badge_filename, b.special
      FROM badge_info_tags_carousel_state AS s
      JOIN badge_info AS b ON s.last_viewed_badge_info_id = b.id
      WHERE s.user_discord_id = %s
    '''
    await query.execute(sql, (user_discord_id,))
    return await query.fetchone()


async def db_upsert_last_carousel_badge_info(user_discord_id, badge_info_id):
  async with AgimusDB() as query:
    sql = '''
      INSERT INTO badge_info_tags_carousel_state (user_discord_id, last_viewed_badge_info_id)
      VALUES (%s, %s) AS new
      ON DUPLICATE KEY UPDATE
        last_viewed_badge_info_id = new.last_viewed_badge_info_id,
        last_modified = CURRENT_TIMESTAMP
    '''
    await query.execute(sql, (user_discord_id, badge_info_id))


async def db_clear_last_carousel_badge_info(user_discord_id):
  async with AgimusDB() as query:
    sql = '''
      DELETE FROM badge_info_tags_carousel_state WHERE user_discord_id = %s
    '''
    await query.execute(sql, (user_discord_id,))
