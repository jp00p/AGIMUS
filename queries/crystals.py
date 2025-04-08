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


async def db_set_slotted_crystal(instance_id: int, crystal_id: int):
  async with AgimusDB() as query:
    await query.execute(
      "UPDATE badge_instances SET preferred_crystal_id = %s WHERE id = %s",
      (crystal_id, instance_id)
    )

async def db_get_crystal_by_id(crystal_id: int) -> dict:
  async with AgimusDB(dictionary=True) as query:
    sql = """
      SELECT ct.*, cr.rarity_rank FROM crystal_types ct
      JOIN crystal_ranks cr ON ct.crystal_rank_rarity = cr.rarity_rank
      WHERE ct.id = %s
    """
    vals = (crystal_id,)
    await query.execute(sql, vals)
    return await query.fetchone()


async def db_check_crystal_attached(badge_instance_id: int, crystal_type_id: int):
  async with AgimusDB() as query:
    await query.execute(
      """
        SELECT 1 FROM badge_crystals
        WHERE badge_instance_id = %s AND crystal_type_id = %s
        LIMIT 1
      """,
      (badge_instance_id, crystal_type_id)
    )
    return await query.fetchone() is not None


async def db_get_attached_crystals(instance_id: int):
  async with AgimusDB(dictionary=True) as query:
    await query.execute(
      """
        SELECT
          bc.id AS badge_crystal_id,
          bc.badge_instance_id,
          bc.crystal_type_id,

          ct.id AS crystal_type_id,
          ct.name AS crystal_name,
          ct.effect,
          ct.description,
          ct.icon,
          ct.crystal_rarity_rank,

          cr.rarity_rank,
          cr.name AS rarity_name,
          cr.emoji,
          cr.drop_chance,
          cr.sort_order

        FROM badge_crystals bc
        JOIN crystal_types ct ON bc.crystal_type_id = ct.id
        JOIN crystal_ranks cr ON ct.crystal_rarity_rank = cr.rarity_rank
        WHERE bc.badge_instance_id = %s
        ORDER BY ct.crystal_rarity_rank, ct.name ASC
      """,
      (instance_id,)
    )
    existing_crystals = await query.fetchall()
  return existing_crystals


async def db_get_instance_by_crystal(crystal_id: int) -> dict | None:
  async with AgimusDB(dictionary=True) as query:
    await query.execute(
      """
      SELECT b.id AS badge_instance_id
      FROM badge_crystals AS bc
      JOIN badge_instances AS b ON bc.badge_instance_id = b.id
      WHERE bc.id = %s
      """,
      (crystal_id,)
    )
    return await query.fetchone()

async def db_get_crystals_by_rarity(rarity_rank: int):
  async with AgimusDB(dictionary=True) as query:
    await query.execute(
      """
        SELECT ct.*, cr.emoji, cr.name AS rarity_name
        FROM crystal_types ct
        JOIN crystal_ranks cr ON ct.crystal_rarity_rank = cr.rarity_rank
        WHERE ct.crystal_rarity_rank = %s
        ORDER BY c.name ASC
      """,
      (rarity_rank,)
    )
    return await query.fetchall()

async def db_get_crystal_rarity_weights():
  async with AgimusDB(dictionary=True) as query:
    await query.execute(
      """
        SELECT rarity_rank, drop_chance
        FROM crystal_ranks
        ORDER BY crystal_rank ASC
      """
    )
    return await query.fetchall()


async def get_rarest_crystal(crystals: list[dict]) -> dict:
  if not crystals:
    return None
  return max(crystals, key=lambda c: c['rarity_rank'])


async def db_get_available_crystal_types():
  async with AgimusDB(dictionary=True) as query:
    await query.execute(
      """
        SELECT c.*, r.emoji, r.drop_chance
        FROM crystal_types c
        JOIN crystal_ranks r ON c.crystal_rarity_rank = r.rarity_rank
        ORDER BY c.crystal_rarity_rank ASC, c.name ASC
      """
    )
    crystal_types = await query.fetchall()
  return crystal_types


async def db_get_crystallize_autoslot_preference(user_id: int) -> str:
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT crystallize_autoslot FROM users WHERE discord_id = %s"
    vals = (user_id,)
    await query.execute(sql, vals)
    result = await query.fetchone()
    return result['crystallize_autoslot'] if result else 'manual'
