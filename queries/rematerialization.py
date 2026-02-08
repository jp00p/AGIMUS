from common import *

# queries.rematerialization

async def db_get_active_rematerialization(user_discord_id: str) -> dict | None:
  sql = """
    SELECT *
    FROM crystal_rematerializations
    WHERE user_discord_id = %s
      AND status = 'active'
    ORDER BY id DESC
    LIMIT 1
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (user_discord_id,))
    return await db.fetchone()

async def db_create_rematerialization(user_discord_id: str, source_rank_id: int, target_rank_id: int) -> int:
  sql = """
    INSERT INTO crystal_rematerializations (
      user_discord_id,
      source_rank_id,
      target_rank_id
    )
    VALUES (%s, %s, %s)
  """
  async with AgimusDB() as db:
    await db.execute(sql, (user_discord_id, source_rank_id, target_rank_id))
    return db.lastrowid

async def db_cancel_rematerialization(rematerialization_id: int):
  sql = """
    UPDATE crystal_rematerializations
    SET status = 'cancelled',
      completed_at = CURRENT_TIMESTAMP
    WHERE id = %s
  """
  async with AgimusDB() as db:
    await db.execute(sql, (rematerialization_id,))

async def db_add_crystal_to_rematerialization(rematerialization_id: int, crystal_instance_id: int):
  sql = """
    INSERT INTO crystal_rematerialization_items (
      rematerialization_id,
      crystal_instance_id
    )
    VALUES (%s, %s)
  """
  async with AgimusDB() as db:
    await db.execute(sql, (rematerialization_id, crystal_instance_id))

async def db_get_rematerialization_items(rematerialization_id: int) -> list[dict]:
  sql = """
    SELECT
      ri.id AS rematerialization_item_id,

      ci.id AS crystal_instance_id,
      ci.owner_discord_id,
      ci.status AS crystal_status,
      ci.created_at AS crystal_created_at,

      ct.id AS crystal_type_id,
      ct.name AS crystal_name,
      ct.effect,
      ct.description,
      ct.icon,
      ct.rarity_rank,

      cr.name AS rarity_name,
      cr.emoji,
      cr.drop_chance,
      cr.sort_order

    FROM crystal_rematerialization_items ri
    JOIN crystal_instances ci ON ri.crystal_instance_id = ci.id
    JOIN crystal_types ct ON ci.crystal_type_id = ct.id
    JOIN crystal_ranks cr ON ct.rarity_rank = cr.rarity_rank
    WHERE ri.rematerialization_id = %s
    ORDER BY ri.id ASC
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (rematerialization_id,))
    return await db.fetchall()

async def db_finalize_rematerialization(rematerialization_id: int):
  sql = """
    UPDATE crystal_rematerializations
    SET status = 'completed',
      completed_at = CURRENT_TIMESTAMP
    WHERE id = %s
  """
  async with AgimusDB() as db:
    await db.execute(sql, (rematerialization_id,))

async def db_mark_crystals_dematerialized(crystal_ids: list[int]):
  if not crystal_ids:
    return

  placeholders = ', '.join(['%s'] * len(crystal_ids))

  sql = f"""
    UPDATE crystal_instances
    SET status = 'dematerialized'
    WHERE id IN ({placeholders})
  """
  async with AgimusDB() as db:
    await db.execute(sql, crystal_ids)

  sql = f"""
    INSERT INTO crystal_instance_history (
      crystal_instance_id,
      event_type,
      to_user_id
    )
    SELECT
      id,
      'dematerialized',
      owner_discord_id
    FROM crystal_instances
    WHERE id IN ({placeholders})
  """
  async with AgimusDB() as db:
    await db.execute(sql, crystal_ids)

async def db_remove_last_rematerialization_item(rematerialization_id: int) -> dict | None:
  sql = """
    SELECT
      ri.id AS rematerialization_item_id,
      ci.id AS crystal_instance_id,
      ct.id AS crystal_type_id
    FROM crystal_rematerialization_items ri
    JOIN crystal_instances ci ON ri.crystal_instance_id = ci.id
    JOIN crystal_types ct ON ci.crystal_type_id = ct.id
    WHERE ri.rematerialization_id = %s
    ORDER BY ri.id DESC
    LIMIT 1
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (rematerialization_id,))
    row = await db.fetchone()

  if not row:
    return None

  sql = """
    DELETE FROM crystal_rematerialization_items
    WHERE id = %s
    LIMIT 1
  """
  async with AgimusDB() as db:
    await db.execute(sql, (row['rematerialization_item_id'],))

  return row

async def db_remove_last_rematerialization_type_batch(rematerialization_id: int) -> list[dict]:
  # Removes the contiguous tail of items that share the same crystal_type_id as the most recent item.
  # Returns the removed rows (crystal_instance_id, crystal_type_id) in the order they were removed.
  sql = """
    SELECT
      ri.id AS rematerialization_item_id,
      ci.id AS crystal_instance_id,
      ct.id AS crystal_type_id
    FROM crystal_rematerialization_items ri
    JOIN crystal_instances ci ON ri.crystal_instance_id = ci.id
    JOIN crystal_types ct ON ci.crystal_type_id = ct.id
    WHERE ri.rematerialization_id = %s
    ORDER BY ri.id DESC
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (rematerialization_id,))
    rows = await db.fetchall()

  if not rows:
    return []

  last_type_id = rows[0]['crystal_type_id']

  # Only remove the contiguous tail matching last_type_id
  to_remove = []
  for row in rows:
    if row['crystal_type_id'] != last_type_id:
      break
    to_remove.append(row)

  if not to_remove:
    return []

  placeholders = ', '.join(['%s'] * len(to_remove))
  ids = [r['rematerialization_item_id'] for r in to_remove]

  sql = f"""
    DELETE FROM crystal_rematerialization_items
    WHERE id IN ({placeholders})
  """
  async with AgimusDB() as db:
    await db.execute(sql, ids)

  return to_remove
