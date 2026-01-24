from common import *

async def db_get_active_rematerialization(user_discord_id: str) -> dict | None:
  sql = """
    SELECT *
    FROM crystal_rematerializations
    WHERE user_discord_id = %s AND status = 'active'
    LIMIT 1
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (user_discord_id,))
    return await db.fetchone()

async def db_create_rematerialization(user_discord_id: int, source_rank_id: int, target_rank_id: int) -> int:
  sql = """
    INSERT INTO crystal_rematerializations (user_discord_id, source_rank_id, target_rank_id)
    VALUES (%s, %s, %s)
  """
  async with AgimusDB() as db:
    await db.execute(sql, (user_discord_id, source_rank_id, target_rank_id))
    return db.lastrowid

async def db_cancel_rematerialization(rematerialization_id: int):
  sql = """
    UPDATE crystal_rematerializations
    SET status = 'cancelled', completed_at = CURRENT_TIMESTAMP
    WHERE id = %s
  """
  async with AgimusDB() as db:
    await db.execute(sql, (rematerialization_id,))

async def db_add_crystal_to_rematerialization(rematerialization_id: int, crystal_instance_id: int):
  sql = """
    INSERT INTO crystal_rematerialization_items (rematerialization_id, crystal_instance_id)
    VALUES (%s, %s)
  """
  async with AgimusDB() as db:
    await db.execute(sql, (rematerialization_id, crystal_instance_id))

async def db_get_rematerialization_items(rematerialization_id: int) -> list[dict]:
  sql = """
    SELECT ci.*, ct.name AS crystal_name, cr.name AS rarity_name, cr.emoji
    FROM crystal_rematerialization_items ri
    JOIN crystal_instances ci ON ri.crystal_instance_id = ci.id
    JOIN crystal_types ct ON ci.crystal_type_id = ct.id
    JOIN crystal_ranks cr ON ct.rarity_rank = cr.rarity_rank
    WHERE ri.rematerialization_id = %s
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (rematerialization_id,))
    return await db.fetchall()

async def db_finalize_rematerialization(rematerialization_id: int):
  sql = """
    UPDATE crystal_rematerializations
    SET status = 'completed', completed_at = CURRENT_TIMESTAMP
    WHERE id = %s
  """
  async with AgimusDB() as db:
    await db.execute(sql, (rematerialization_id,))

async def db_mark_crystals_dematerialized(crystal_ids: list[int]):
  if not crystal_ids:
    return

  placeholders = ', '.join(['%s'] * len(crystal_ids))

  sql_update = f"""
    UPDATE crystal_instances
    SET status = 'rematerialized'
    WHERE id IN ({placeholders})
  """

  sql_history = f"""
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
    await db.execute(sql_update, crystal_ids)
    await db.execute(sql_history, crystal_ids)