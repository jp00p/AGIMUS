from common import *


async def db_insert_badge_instance_if_missing(user_id: int, badge_info_id: int):
  async with AgimusDB(dictionary=True) as query:
    await query.execute(
      "SELECT id FROM badge_instances WHERE badge_info_id = %s AND owner_discord_id = %s",
      (badge_info_id, user_id)
    )
    existing = await query.fetchone()
    if existing:
      return None

    await query.execute(
      "INSERT INTO badge_instances (badge_info_id, owner_discord_id, locked) VALUES (%s, %s, %s)",
      (badge_info_id, user_id, False)
    )
    return { "id": query.lastrowid }


async def db_attach_crystal_to_instance(instance_id: int, crystal_name: str = "Dilithium") -> Optional[int]:
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
    return query.lastrowid


async def db_set_preferred_crystal(instance_id: int, crystal_id: int):
  async with AgimusDB() as query:
    await query.execute(
      "UPDATE badge_instances SET preferred_crystal_id = %s WHERE id = %s",
      (crystal_id, instance_id)
    )
