from common import *

# utils/badge_instances.py

async def transfer_badge_instance(instance_id: int, to_user_id: int, reason: str = 'unknown'):
  """
  Transfers a badge instance to a new owner and logs the provenance record.

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
    INSERT INTO badge_instance_provenance (badge_instance_id, from_user_id, to_user_id, acquisition_reason)
    VALUES (%s, %s, %s, %s)
  """

  async with AgimusDB(dictionary=True) as db:
    row = await db.fetchone(query_fetch, (instance_id,))
    from_user_id = int(row['owner_discord_id']) if row and row['owner_discord_id'] is not None else None

    await db.execute(query_update, (to_user_id, instance_id))
    await db.execute(query_insert, (instance_id, from_user_id, to_user_id, reason))


async def db_liquidate_badge_instance(instance_id: int):
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
  query_provenance = """
    INSERT INTO badge_instance_provenance (badge_instance_id, from_user_id, to_user_id, acquisition_reason)
    VALUES (%s, %s, NULL, 'liquidation')
  """
  async with AgimusDB() as db:
    await db.execute(query_provenance, (instance_id, old_owner))

