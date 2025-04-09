from common import *

# utils/badge_instances.py

async def get_badge_instance_with_info(instance_id: int) -> dict:
  query = """
    SELECT
      b_inst.id AS id,
      b_inst.badge_info_id,
      b_inst.owner_discord_id,
      b_inst.locked,
      b_inst.origin_user_id,
      b_inst.acquired_at,
      b_inst.slotted_crystal_id,
      b_inst.status,

      b_i.id AS badge_info_id,
      b_i.badge_filename,
      b_i.badge_name,
      b_i.badge_url,
      b_i.quadrant,
      b_i.time_period,
      b_i.franchise,
      b_i.reference,
      b_i.special
    FROM badge_instances AS b_inst
    JOIN badge_info AS b_i ON b_inst.badge_info_id = b_i.id
    WHERE b_inst.id = %s
  """
  async with AgimusDB(dictionary=True) as db:
    return await db.fetchone(query, (instance_id,))


async def create_new_badge_instance(badge_info_id: int, user_id: int, reason: str = 'level_up') -> dict:
  # Insert a new active, unlocked badge instance
  insert_instance = """
    INSERT INTO badge_instances (badge_info_id, owner_discord_id, status)
    VALUES (%s, %s, 'active')
  """
  async with AgimusDB() as db:
    await db.execute(insert_instance, (badge_info_id, user_id))
    instance_id = db.lastrowid

  # Log acquisition in history
  insert_history = """
    INSERT INTO badge_instance_history (badge_instance_id, from_user_id, to_user_id, acquisition_reason)
    VALUES (%s, NULL, %s, %s)
  """
  async with AgimusDB() as db:
    await db.execute(insert_history, (instance_id, user_id, reason))

  # Fetch full record with badge info
  return await get_badge_instance_with_info(instance_id)


async def transfer_badge_instance(instance_id: int, to_user_id: int, reason: str = 'trade'):
  """
  Transfers a badge instance to a new owner and logs the history record.

  Args:
    instance_id (int): ID of the badge_instances row.
    to_user_id (int): Discord user ID (int) of the new owner.
    reason (str): One of the allowed acquisition reasons. Defaults to 'unknown'.
  """
  query_fetch = """
    SELECT owner_discord_id
    FROM badge_instances
    WHERE id = %s
  """

  query_update = """
    UPDATE badge_instances
    SET owner_discord_id = %s
    WHERE id = %s
  """

  query_insert = """
    INSERT INTO badge_instance_history (badge_instance_id, from_user_id, to_user_id, acquisition_reason)
    VALUES (%s, %s, %s, %s)
  """

  async with AgimusDB(dictionary=True) as db:
    row = await db.fetchone(query_fetch, (instance_id,))
    from_user_id = int(row['owner_discord_id']) if row and row['owner_discord_id'] is not None else None

    await db.execute(query_update, (to_user_id, instance_id))
    await db.execute(query_insert, (instance_id, from_user_id, to_user_id, reason))


async def liquidate_badge_instance(instance_id: int):
  # Fetch old owner
  query_owner = """
    SELECT owner_discord_id
    FROM badge_instances
    WHERE id = %s
  """
  async with AgimusDB(dictionary=True) as db:
    old = await db.fetchone(query_owner, (instance_id,))
    old_owner = old['owner_discord_id'] if old else None

  # Update badge instance to unowned + liquidated
  query_update = """
    UPDATE badge_instances
    SET owner_discord_id = NULL,
        status = 'liquidated'
    WHERE id = %s
  """
  async with AgimusDB() as db:
    await db.execute(query_update, (instance_id,))

  # Record provenance
  query_history = """
    INSERT INTO badge_instance_history (badge_instance_id, from_user_id, to_user_id, acquisition_reason)
    VALUES (%s, %s, NULL, 'liquidation')
  """
  async with AgimusDB() as db:
    await db.execute(query_history, (instance_id, old_owner))
