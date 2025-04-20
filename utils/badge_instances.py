from common import *

# utils/badge_instances.py

from queries.badge_instances import *

async def create_new_badge_instance(user_id: int, badge_info_id: int, event_type: str = 'level_up') -> dict:
  # Insert a new active, unlocked badge instance
  insert_instance = """
    INSERT INTO badge_instances (badge_info_id, owner_discord_id, origin_user_id, status)
    VALUES (%s, %s, %s, 'active')
  """
  async with AgimusDB() as db:
    await db.execute(insert_instance, (badge_info_id, user_id, user_id))
    instance_id = db.lastrowid

  # Log acquisition in history
  insert_history = """
    INSERT INTO badge_instance_history (badge_instance_id, from_user_id, to_user_id, event_type)
    VALUES (%s, NULL, %s, %s)
  """
  async with AgimusDB() as db:
    await db.execute(insert_history, (instance_id, user_id, event_type))

  # Fetch full record with badge info
  instance = await db_get_badge_instance_by_id(instance_id)
  return instance


async def transfer_badge_instance(instance_id: int, to_user_id: int, event_type: str = 'unknown'):
  """
  Transfers a badge instance to a new owner and logs the history record.

  Args:
    instance_id (int): ID of the badge_instances row.
    to_user_id (int): Discord user ID (int) of the new owner.
    event_type (str): One of the allowed event_types. Defaults to 'unknown'.
  """
  query_fetch = """
    SELECT owner_discord_id
    FROM badge_instances
    WHERE id = %s
  """

  query_update = """
    UPDATE badge_instances
    SET owner_discord_id = %s locked = FALSE
    WHERE id = %s
  """

  query_insert = """
    INSERT INTO badge_instance_history (badge_instance_id, from_user_id, to_user_id, event_type)
    VALUES (%s, %s, %s, %s)
  """

  async with AgimusDB(dictionary=True) as db:
    await db.execute(query_fetch, (instance_id,))
    row = await db.fetchone()
    from_user_id = int(row['owner_discord_id']) if row and row['owner_discord_id'] is not None else None

    await db.execute(query_update, (to_user_id, instance_id))
    await db.execute(query_insert, (instance_id, from_user_id, to_user_id, event_type))


async def liquidate_badge_instance(instance_id: int):
  # Fetch old owner
  query_owner = """
    SELECT owner_discord_id
    FROM badge_instances
    WHERE id = %s
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(query_owner, (instance_id,))
    old = await db.fetchone()
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

  # Record history
  query_history = """
    INSERT INTO badge_instance_history (badge_instance_id, from_user_id, to_user_id, event_type)
    VALUES (%s, %s, NULL, 'liquidation')
  """
  async with AgimusDB() as db:
    await db.execute(query_history, (instance_id, old_owner))


async def log_badge_instance_history(
  badge_instance_id: int,
  event_type: str,
  to_user_id: int | None = None,
  from_user_id: int | None = None,
  occurred_at: datetime | None = None
):
  """
  Inserts a record into badge_instance_history to track ownership changes and system events.

  Args:
    badge_instance_id (int): The badge_instances.id being modified.
    to_user_id (int): The user receiving the badge, or NULL if badge is being removed.
    event_type (str): One of the valid enum values: 'tongo_venture', 'trade', etc.
    from_user_id (int | None): Optional user the badge is being transferred from.
    occurred_at (datetime | None): Optional manual timestamp. Defaults to NOW.
  """
  async with AgimusDB() as db:
    query = """
      INSERT INTO badge_instance_history (
        badge_instance_id, event_type, from_user_id, to_user_id, occurred_at
      ) VALUES (%s, %s, %s, %s, %s)
    """
    await db.execute(
      query,
      (
        badge_instance_id,
        event_type or 'unknown',
        from_user_id,
        to_user_id,
        occurred_at or datetime.utcnow()
      )
    )
