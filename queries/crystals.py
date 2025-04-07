from common import *


async def db_attach_crystal_to_instance(instance_id: int, crystal_name: str = "Dilithium"):
  async with AgimusDB(dictionary=True) as query:
    await query.execute("SELECT id FROM crystal_types WHERE name = %s", (crystal_name,))
    crystal_type = await query.fetchone()
    if not crystal_type:
      raise RuntimeError(f"Crystal type '{crystal_name}' not found")

    await query.execute(
      "SELECT id FROM badge_crystals WHERE badge_instance_id = %s AND crystal_type_id = %s",
      (instance_id, crystal_type["id"])
    )
    if await query.fetchone():
      return None

    await query.execute(
      "INSERT INTO badge_crystals (badge_instance_id, crystal_type_id) VALUES (%s, %s)",
      (instance_id, crystal_type["id"])
    )
    crystal_id = query.lastrowid

    await query.execute("SELECT * FROM badge_crystals WHERE id = %s", (crystal_id,))
    crystal = await query.fetchone()
  return crystal


async def db_set_preferred_crystal(instance_id: int, crystal_id: int):
  async with AgimusDB() as query:
    await query.execute(
      "UPDATE badge_instances SET preferred_crystal_id = %s WHERE id = %s",
      (crystal_id, instance_id)
    )


async def db_get_existing_crystals_for_instance(instance_id: int):
  async with AgimusDB(dictionary=True) as query:
    await query.execute(
      """
        SELECT bc.*, ct.*
        FROM badge_crystals bc
        JOIN crystal_types ct ON bc.crystal_type_id = ct.id
        JOIN crystal_ranks cr ON ct.crystal_rarity_rank = cr.rarity_rank
        WHERE bc.badge_instance_id = %s
      """,
      (instance_id,)
    )
    existing_crystals = await query.fetchall()
  return existing_crystals


async def db_get_available_crystal_types():
  async with AgimusDB(dictionary=True) as query:
    await query.execute(
      """
        SELECT c.*, r.emoji, r.drop_chance
        FROM crystal_types c
        JOIN crystal_ranks r ON c.crystal_rarity_rank = r.rarity_rank
      """
    )
    crystal_types = await query.fetchall()
  return crystal_types

