from datetime import datetime
from common import *
from queries.crystal_instances import *

async def create_new_crystal_instance(user_id: int, crystal_type_id: int, event_type='replicated') -> dict:
  """
  Creates a new available crystal_instance, logs the history, and returns the enriched instance.

  Args:
    user_id (int): Discord user ID receiving the crystal
    crystal_type_id (int): ID from crystal_types
    event_type (str): One of the valid crystal_instance_history types

  Returns:
    dict: Full enriched crystal_instance joined with crystal_types and crystal_ranks
  """
  async with AgimusDB() as db:
    # Insert instance
    await db.execute(
      """
      INSERT INTO crystal_instances (crystal_type_id, owner_discord_id, status)
      VALUES (%s, %s, 'available')
      """,
      (crystal_type_id, user_id)
    )
    instance_id = db.lastrowid

    # Insert history
    await db.execute(
      """
      INSERT INTO crystal_instance_history (crystal_instance_id, event_type, to_user_id)
      VALUES (%s, %s, %s)
      """,
      (instance_id, event_type, user_id)
    )

  # Return enriched result
  return await db_get_crystal_by_id(instance_id)


async def attune_crystal_to_badge(crystal_instance_id: int, badge_instance_id: int):
  """
  Attaches a crystal_instance to a badge_instance permanently.

  Args:
    crystal_instance_id (int): The ID of the crystal_instance.
    badge_instance_id (int): The ID of the badge_instance to attune to.
  """
  async with AgimusDB() as db:
    # Insert into badge_crystals
    await db.execute(
      """
      INSERT INTO badge_crystals (badge_instance_id, crystal_instance_id)
      VALUES (%s, %s)
      """,
      (badge_instance_id, crystal_instance_id)
    )

    # Update status and linkage
    await db.execute(
      """
      UPDATE crystal_instances
      SET status = 'attuned',
          attached_to_instance_id = %s
      WHERE id = %s
      """,
      (badge_instance_id, crystal_instance_id)
    )

    # Log history
    await db.execute(
      """
      INSERT INTO crystal_instance_history (crystal_instance_id, event_type, to_user_id)
      VALUES (%s, 'attuned', (SELECT owner_discord_id FROM badge_instances WHERE id = %s))
      """,
      (crystal_instance_id, badge_instance_id)
    )


async def transfer_crystal_instance(crystal_instance_id: int, to_user_id: int, event_type: str = 'trade'):
  """
  Transfers a crystal_instance to a new user and logs the transfer in history.

  Args:
    crystal_instance_id (int): ID of the crystal_instances row.
    to_user_id (int): Discord user ID receiving the crystal.
    event_type (str): One of the valid crystal_instance_history event types.
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute("SELECT owner_discord_id FROM crystal_instances WHERE id = %s", (crystal_instance_id,))
    row = await db.fetchone()
    from_user_id = row['owner_discord_id'] if row else None

  async with AgimusDB() as db:
    await db.execute(
      "UPDATE crystal_instances SET owner_discord_id = %s WHERE id = %s",
      (to_user_id, crystal_instance_id)
    )
    await db.execute(
      """
      INSERT INTO crystal_instance_history (crystal_instance_id, from_user_id, to_user_id, event_type)
      VALUES (%s, %s, %s, %s)
      """,
      (crystal_instance_id, from_user_id, to_user_id, event_type)
    )


async def log_crystal_instance_history(
  crystal_instance_id: int,
  event_type: str,
  to_user_id: int | None = None,
  from_user_id: int | None = None,
  occurred_at: datetime | None = None
):
  """
  Logs an event to crystal_instance_history.

  Args:
    crystal_instance_id (int): ID of the crystal_instances row.
    event_type (str): e.g. 'replicated', 'trade', 'attached'
    to_user_id (int | None): The user receiving the crystal (if applicable)
    from_user_id (int | None): The user giving the crystal (if applicable)
    occurred_at (datetime | None): Optional manual timestamp
  """
  async with AgimusDB() as db:
    await db.execute(
      """
      INSERT INTO crystal_instance_history (
        crystal_instance_id, event_type, from_user_id, to_user_id, occurred_at
      ) VALUES (%s, %s, %s, %s, %s)
      """,
      (
        crystal_instance_id,
        event_type,
        from_user_id,
        to_user_id,
        occurred_at or datetime.utcnow()
      )
    )

# Used by cogs.crystals and cogs.tongo to reward Crystals based on Rarity Drop Chances
def weighted_random_choice(weight_map: dict[str, float]) -> str:
    """
    Returns a single key from the dict based on its weight.
    Keys are possible values, values are weights (drop chances).
    """
    choices = list(weight_map.keys())
    weights = list(weight_map.values())
    return random.choices(choices, weights=weights, k=1)[0]