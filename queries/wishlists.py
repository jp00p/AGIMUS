from typing import Literal

from common import AgimusDB
from queries.common import BADGE_INSTANCE_COLUMNS
import json

# Add
async def db_add_badge_info_id_to_wishlist(user_discord_id: str, badge_info_id: int):
  sql = '''
    INSERT INTO badge_instances_wishlists (user_discord_id, badge_info_id)
    VALUES (%s, %s)
    ON DUPLICATE KEY UPDATE time_added = time_added;
  '''
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (user_discord_id, badge_info_id))

async def db_add_badge_info_ids_to_wishlist(user_discord_id: str, badge_info_ids: list[int]):
  """
  Bulk add multiple badge_info entries to a user's prime wishlist.
  Uses INSERT IGNORE to avoid duplicate constraint errors.
  """
  # Prepare (user_id, badge_info_id) tuples for executemany
  values = [(user_discord_id, badge_id) for badge_id in badge_info_ids]
  sql = '''
    INSERT IGNORE INTO badge_instances_wishlists (user_discord_id, badge_info_id)
    VALUES (%s, %s)
    ON DUPLICATE KEY UPDATE time_added = time_added;
  '''
  async with AgimusDB() as db:
    await db.executemany(sql, values)

# Remove
async def db_remove_badge_info_id_from_wishlist(user_discord_id: str, badge_info_id: int):
  async with AgimusDB(dictionary=True) as db:
    # Remove from wishlist
    await db.execute('''
      DELETE FROM badge_instances_wishlists
      WHERE user_discord_id = %s
        AND badge_info_id = %s;
    ''', (user_discord_id, badge_info_id))

    # Also remove any dismissal rows tied to this badge
    await db.execute('''
      DELETE FROM badge_instances_wishlists_dismissals
      WHERE user_discord_id = %s
        AND badge_info_id = %s;
    ''', (user_discord_id, badge_info_id))

async def db_remove_badge_info_ids_from_wishlist(user_discord_id: str, badge_info_ids: list[int]):
  values = [(user_discord_id, bid) for bid in badge_info_ids]

  async with AgimusDB(dictionary=True) as db:
    # Remove from wishlist
    sql = '''
      DELETE FROM badge_instances_wishlists
      WHERE user_discord_id = %s
        AND badge_info_id = %s;
    '''
    await db.executemany(sql, values)

    # Remove dismissals for these badge_info_ids
    sql_dismissals = '''
      DELETE FROM badge_instances_wishlists_dismissals
      WHERE user_discord_id = %s
        AND badge_info_id = %s;
    '''
    await db.executemany(sql_dismissals, values)

async def db_clear_wishlist(user_discord_id: str):
  async with AgimusDB(dictionary=True) as db:
    # Remove all wishlist entries
    await db.execute('''
      DELETE FROM badge_instances_wishlists
      WHERE user_discord_id = %s;
    ''', (user_discord_id,))

    # Also clear all dismissals authored by this user
    await db.execute('''
      DELETE FROM badge_instances_wishlists_dismissals
      WHERE user_discord_id = %s;
    ''', (user_discord_id,))

# CHECK
async def db_is_badge_on_users_wishlist(user_discord_id: str, badge_info_id: str):
  sql = '''
    SELECT 1
    FROM badge_instances_wishlists w
    JOIN badge_info bi ON bi.id = w.badge_info_id
    WHERE w.user_discord_id = %s
      AND bi.id = %s
    LIMIT 1;
  '''
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (user_discord_id, badge_info_id))
    return await db.fetchone() is not None

# LOCKING
async def db_lock_badge_instances_by_badge_info_id(user_discord_id: str, badge_info_id: int):
  """
  Lock all active badge instances for a user matching the given badge_info_id.
  """
  sql = '''
    UPDATE badge_instances
    SET locked = TRUE
    WHERE owner_discord_id = %s
      AND badge_info_id = %s
      AND active = TRUE;
  '''
  async with AgimusDB() as db:
    await db.execute(sql, (user_discord_id, badge_info_id))

async def db_lock_badge_instances_by_badge_info_ids(user_discord_id: str, badge_info_ids: list[int]):
  """
  Bulk lock all active badge instances for a user across multiple badge_info_ids.
  """
  values = [(user_discord_id, badge_id) for badge_id in badge_info_ids]
  sql = '''
    UPDATE badge_instances
    SET locked = TRUE
    WHERE owner_discord_id = %s
      AND badge_info_id = %s
      AND active = TRUE;
  '''
  async with AgimusDB() as db:
    await db.executemany(sql, values)

async def db_unlock_badge_instances_by_badge_info_id(user_discord_id: str, badge_info_id: int):
  """
  Lock all active badge instances for a user matching the given badge_info_id.
  """
  sql = '''
    UPDATE badge_instances
    SET locked = FALSE
    WHERE owner_discord_id = %s
      AND badge_info_id = %s
      AND active = TRUE;
  '''
  async with AgimusDB() as db:
    await db.execute(sql, (user_discord_id, badge_info_id))

async def db_unlock_badge_instances_by_badge_info_ids(user_discord_id: str, badge_info_ids: list[int]):
  """
  Bulk lock all active badge instances for a user across multiple badge_info_ids.
  """
  values = [(user_discord_id, badge_id) for badge_id in badge_info_ids]
  sql = '''
    UPDATE badge_instances
    SET locked = FALSE
    WHERE owner_discord_id = %s
      AND badge_info_id = %s
      AND active = TRUE;
  '''
  async with AgimusDB() as db:
    await db.executemany(sql, values)

# GET
async def db_get_full_wishlist_badges(
    user_discord_id: str,
    *,
    prestige: int | None = None
) -> list[dict]:
  """
  Returns enriched badge rows from the user's prime wishlist.
  If `prestige` is None, returns *all* wishlist entries (with NULL instance fields).
  If `prestige` is provided, only returns those badges for which the user
  has an unlocked, active instance at that prestige level.
  """
  # Base SELECT + joins on badge_info/crystals/etc.
  base_sql = f"""
    SELECT {BADGE_INSTANCE_COLUMNS}
    FROM badge_instances_wishlists w
    JOIN badge_info bi
      ON w.badge_info_id = bi.id
  """

  # If prestige is specified, INNER JOIN instances at that level:
  if prestige is not None:
    base_sql += """
      JOIN badge_instances b
        ON b.badge_info_id   = bi.id
        AND b.owner_discord_id = %s
        AND b.prestige_level   = %s
        AND b.active           = TRUE
        AND b.locked           = FALSE
    """
    params = [user_discord_id, prestige]
  else:
    # Otherwise, LEFT JOIN so we still get every wishlist entry:
    base_sql += """
      LEFT JOIN badge_instances b
        ON b.badge_info_id   = bi.id
        AND b.owner_discord_id = %s
        AND b.active           = TRUE
        AND b.locked           = FALSE
    """
    params = [user_discord_id]

  # Attach the remaining crystal joins and WHERE clause:
  base_sql += """
    LEFT JOIN badge_crystals    c  ON b.active_crystal_id    = c.id
    LEFT JOIN crystal_instances ci ON c.crystal_instance_id  = ci.id
    LEFT JOIN crystal_types     t  ON ci.crystal_type_id     = t.id
    WHERE w.user_discord_id = %s
    ORDER BY bi.badge_name ASC;
  """

  # Always need to pass user_discord_id again for the WHERE
  params.append(user_discord_id)

  async with AgimusDB(dictionary=True) as db:
    await db.execute(base_sql, params)
    return await db.fetchall()


async def db_get_simple_wishlist_badges(user_discord_id: str) -> list[dict]:
  """
  Returns just the basic badge information from the user's prime wishlist:
    - badge_info_id
    - badge_name
    - badge_filename
  """
  sql = '''
    SELECT bi.id AS badge_info_id,
           bi.badge_name,
           bi.badge_filename
    FROM badge_instances_wishlists w
    JOIN badge_info bi ON bi.id = w.badge_info_id
    WHERE w.user_discord_id = %s
    ORDER BY bi.badge_name ASC;
  '''
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (user_discord_id,))
    return await db.fetchall()


# Compute "active wants": badges user still needs at a given prestige level
async def db_get_active_wants(user_discord_id: str, prestige_level: int) -> list[dict]:
  sql = '''
    SELECT bi.id AS badge_info_id,
          bi.badge_name,
          bi.badge_url,
          bi.badge_filename
    FROM badge_instances_wishlists w
    JOIN badge_info bi ON bi.id = w.badge_info_id
    WHERE w.user_discord_id = %s
      AND bi.special = FALSE
      AND NOT EXISTS (
        SELECT 1
        FROM badge_instances i
        WHERE i.owner_discord_id = w.user_discord_id
          AND i.badge_info_id = w.badge_info_id
          AND i.prestige_level = %s
          AND i.active = TRUE
      )
    ORDER BY bi.badge_name ASC;
  '''
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (user_discord_id, prestige_level))
    return await db.fetchall()

# Generate wishlist matches via SQL CTE
async def db_get_wishlist_matches(user_discord_id: str, prestige_level: int) -> list[dict]:
  sql = '''
    WITH
      my_unfulfilled_wishlist AS (
        SELECT w.badge_info_id
        FROM badge_instances_wishlists w
        JOIN badge_info bi
          ON bi.id = w.badge_info_id
         AND bi.special = FALSE
        WHERE w.user_discord_id = %s
          AND NOT EXISTS (
            SELECT 1
            FROM badge_instances i
            WHERE i.owner_discord_id = %s
              AND i.badge_info_id = w.badge_info_id
              AND i.prestige_level = %s
              AND i.active = TRUE
          )
      ),
      my_offerable_badges AS (
        SELECT DISTINCT b.badge_info_id
        FROM badge_instances b
        WHERE b.owner_discord_id = %s
          AND b.prestige_level = %s
          AND b.locked = FALSE
          AND b.active = TRUE
      ),
      partner_offerable_badges AS (
        SELECT DISTINCT b.owner_discord_id AS partner_id,
                        b.badge_info_id
        FROM badge_instances b
        WHERE b.prestige_level = %s
          AND b.locked = FALSE
          AND b.active = TRUE
          AND b.badge_info_id IN (SELECT badge_info_id FROM my_unfulfilled_wishlist)
          AND NOT EXISTS (
            SELECT 1
            FROM badge_instances mine
            WHERE mine.owner_discord_id = %s
              AND mine.badge_info_id = b.badge_info_id
              AND mine.prestige_level = b.prestige_level
              AND mine.active = TRUE
          )
      ),
      partner_unfulfilled_wishlist AS (
        SELECT DISTINCT w.user_discord_id AS partner_id,
                        w.badge_info_id
        FROM badge_instances_wishlists w
        JOIN badge_info bi
          ON bi.id = w.badge_info_id
         AND bi.special = FALSE
        WHERE w.badge_info_id IN (SELECT badge_info_id FROM my_offerable_badges)
          AND NOT EXISTS (
            SELECT 1
            FROM badge_instances i
            WHERE i.owner_discord_id = w.user_discord_id
              AND i.badge_info_id = w.badge_info_id
              AND i.prestige_level = %s
              AND i.active = TRUE
          )
      ),
      matched_partners AS (
        SELECT DISTINCT pob.partner_id
        FROM partner_offerable_badges pob
        JOIN partner_unfulfilled_wishlist puw
          ON puw.partner_id = pob.partner_id
        WHERE pob.partner_id != %s
      )
    SELECT
      mp.partner_id AS match_discord_id,

      (
        SELECT JSON_ARRAYAGG(
          JSON_OBJECT('name', bi.badge_name, 'url', bi.badge_url)
        )
        FROM (
          SELECT DISTINCT badge_info_id
          FROM partner_offerable_badges
          WHERE partner_id = mp.partner_id
        ) AS sub
        JOIN badge_info bi ON bi.id = sub.badge_info_id
        ORDER BY bi.badge_name
      ) AS badges_you_want_that_they_have,

      (
        SELECT JSON_ARRAYAGG(sub.badge_info_id)
        FROM (
          SELECT DISTINCT pob.badge_info_id, bi.badge_name
          FROM partner_offerable_badges pob
          JOIN badge_info bi ON bi.id = pob.badge_info_id
          WHERE pob.partner_id = mp.partner_id
          ORDER BY bi.badge_name
        ) AS sub
      ) AS badge_ids_you_want_that_they_have,

      (
        SELECT JSON_ARRAYAGG(
          JSON_OBJECT('name', bi.badge_name, 'url', bi.badge_url)
        )
        FROM (
          SELECT DISTINCT badge_info_id
          FROM partner_unfulfilled_wishlist
          WHERE partner_id = mp.partner_id
        ) AS sub
        JOIN badge_info bi ON bi.id = sub.badge_info_id
        ORDER BY bi.badge_name
      ) AS badges_they_want_that_you_have,

      (
        SELECT JSON_ARRAYAGG(sub.badge_info_id)
        FROM (
          SELECT DISTINCT puw.badge_info_id, bi.badge_name
          FROM partner_unfulfilled_wishlist puw
          JOIN badge_info bi ON bi.id = puw.badge_info_id
          WHERE puw.partner_id = mp.partner_id
          ORDER BY bi.badge_name
        ) AS sub
      ) AS badge_ids_they_want_that_you_have

    FROM matched_partners mp;
  '''

  params = (
    user_discord_id,  # my_unfulfilled_wishlist
    user_discord_id,  # my_unfulfilled_wishlist NOT EXISTS
    prestige_level,

    user_discord_id,  # my_offerable_badges
    prestige_level,

    prestige_level,   # partner_offerable_badges
    user_discord_id,  # partner_offerable_badges NOT EXISTS

    prestige_level,   # partner_unfulfilled_wishlist NOT EXISTS
    user_discord_id   # exclude self
  )

  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, params)
    return await db.fetchall()


# Inventory matches: badges user owns that are in others' prime wishlists
async def db_get_wishlist_inventory_matches(user_discord_id: str, prestige_level: int) -> list[dict]:
  sql = '''
    SELECT bi.*, w.user_discord_id
    FROM badge_instances b
    JOIN badge_info bi ON b.badge_info_id = bi.id
    JOIN badge_instances_wishlists w ON w.badge_info_id = bi.id
    WHERE b.owner_discord_id = %s
      AND b.prestige_level = %s
      AND b.locked = FALSE
      AND b.active = TRUE;
  '''
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (user_discord_id, prestige_level))
    return await db.fetchall()

# Dismissals
async def db_add_wishlist_dismissal(
  user_discord_id: str,
  match_discord_id: str,
  badge_info_id: int,
  prestige_level: int,
  role: Literal['has','wants'],
):
  sql = '''
    INSERT IGNORE INTO badge_instances_wishlists_dismissals
      (user_discord_id, match_discord_id, badge_info_id, prestige_level, role)
    VALUES (%s, %s, %s, %s, %s)
  '''
  async with AgimusDB() as db:
    await db.execute(sql,
      (user_discord_id, match_discord_id, badge_info_id, prestige_level, role)
    )

async def db_delete_wishlist_dismissal(
  user_discord_id: str,
  match_discord_id: str,
  prestige_level: int,
):
  sql = '''
    DELETE FROM badge_instances_wishlists_dismissals
    WHERE user_discord_id   = %s
      AND match_discord_id  = %s
      AND prestige_level    = %s
  '''
  async with AgimusDB() as db:
    await db.execute(sql, (user_discord_id, match_discord_id, prestige_level))


async def db_get_all_wishlist_dismissals(user_discord_id: str) -> list[dict]:
  """
  Fetch all dismissal records for a user's prime wishlist matches.
  Returns rows with fields: user_discord_id, match_discord_id, badge_info_id, prestige_level, role, time_created
  """
  sql = '''
    SELECT
      user_discord_id,
      match_discord_id,
      badge_info_id,
      prestige_level,
      role,
      time_created
    FROM badge_instances_wishlists_dismissals
    WHERE user_discord_id = %s
    ORDER BY time_created ASC;
  '''
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (user_discord_id,))
    return await db.fetchall()

async def db_has_user_opted_out_of_prestige_matches(user_id: str, prestige: int) -> bool:
  sql = '''
    SELECT 1 FROM wishlist_match_opt_outs
    WHERE user_discord_id = %s AND prestige_level = %s
    LIMIT 1
  '''
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (user_id, prestige))
    return await db.fetchone() is not None

async def db_get_all_prestige_match_opted_out_user_ids(prestige: int) -> list[str]:
  sql = '''
    SELECT user_discord_id
    FROM wishlist_match_opt_outs
    WHERE prestige_level = %s
  '''
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (prestige,))
    return [row['user_discord_id'] for row in await db.fetchall()]

async def db_add_prestige_opt_out(user_id: str, prestige: int):
  sql = '''
    INSERT IGNORE INTO wishlist_match_opt_outs (user_discord_id, prestige_level)
    VALUES (%s, %s)
  '''
  async with AgimusDB() as db:
    await db.execute(sql, (user_id, prestige))

async def db_remove_prestige_opt_out(user_id: str, prestige: int):
  sql = '''
    DELETE FROM wishlist_match_opt_outs
    WHERE user_discord_id = %s AND prestige_level = %s
  '''
  async with AgimusDB() as db:
    await db.execute(sql, (user_id, prestige))

async def db_get_opted_out_prestiges(user_id: str) -> list[int]:
  sql = '''
    SELECT prestige_level
    FROM wishlist_match_opt_outs
    WHERE user_discord_id = %s
  '''
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (user_id,))
    return [row['prestige_level'] for row in await db.fetchall()]