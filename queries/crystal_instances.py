from common import *

# queries.crystal_instances

async def db_get_harmonized_crystal(badge_instance_id: int):
  sql = """
    SELECT
      bc.id AS badge_crystal_id,
      bc.badge_instance_id,

      ci.id AS crystal_instance_id,
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

    FROM badge_instances bi
    JOIN badge_crystals bc ON bi.active_crystal_id = bc.id
    JOIN crystal_instances ci ON bc.crystal_instance_id = ci.id
    JOIN crystal_types ct ON ci.crystal_type_id = ct.id
    JOIN crystal_ranks cr ON ct.rarity_rank = cr.rarity_rank
    WHERE bi.id = %s
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (badge_instance_id,))
    return await db.fetchone()


async def db_get_crystal_by_id(crystal_id: int) -> dict | None:
  sql = """
    SELECT
      bc.id AS badge_crystal_id,
      bc.badge_instance_id,
      bc.attached_at,

      ci.id AS crystal_instance_id,
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

    FROM crystal_instances ci
    JOIN crystal_types ct ON ci.crystal_type_id = ct.id
    JOIN crystal_ranks cr ON ct.rarity_rank = cr.rarity_rank
    LEFT JOIN badge_crystals bc ON bc.crystal_instance_id = ci.id
    WHERE ci.id = %s
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (crystal_id,))
    return await db.fetchone()


async def db_check_crystal_attuned(badge_instance_id: int, crystal_type_id: int):
  sql = """
    SELECT 1
    FROM badge_crystals AS bc
    JOIN crystal_instances AS ci ON bc.crystal_instance_id = ci.id
    WHERE bc.badge_instance_id = %s AND ci.crystal_type_id = %s
    LIMIT 1
  """
  async with AgimusDB() as db:
    await db.execute(sql, (badge_instance_id, crystal_type_id))
    return await db.fetchone() is not None


async def db_get_attuned_crystals(badge_instance_id: int) -> list[dict]:
  sql = """
    SELECT
      bc.id AS badge_crystal_id,
      bc.badge_instance_id,
      bc.attached_at,

      ci.id AS crystal_instance_id,
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

    FROM badge_crystals bc
    JOIN crystal_instances ci ON bc.crystal_instance_id = ci.id
    JOIN crystal_types ct ON ci.crystal_type_id = ct.id
    JOIN crystal_ranks cr ON ct.rarity_rank = cr.rarity_rank
    WHERE bc.badge_instance_id = %s
    ORDER BY ct.rarity_rank, ct.name ASC
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (badge_instance_id,))
    return await db.fetchall()

async def db_get_attuned_crystal_type_ids(badge_instance_id: int) -> list[int]:
  sql = """
    SELECT ct.id AS crystal_type_id
    FROM badge_crystals bc
    JOIN crystal_instances ci ON bc.crystal_instance_id = ci.id
    JOIN crystal_types ct ON ci.crystal_type_id = ct.id
    WHERE bc.badge_instance_id = %s
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (badge_instance_id,))
    rows = await db.fetchall()
    return [row['crystal_type_id'] for row in rows]


async def db_get_instance_by_attuned_crystal_id(crystal_id: int) -> dict | None:
  sql = """
    SELECT b.id AS badge_instance_id
    FROM badge_crystals AS bc
    JOIN badge_instances AS b ON bc.badge_instance_id = b.id
    WHERE bc.id = %s
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (crystal_id,))
    return await db.fetchone()


# Rarities
async def db_get_all_crystal_rarity_ranks():
  sql = """
    SELECT id, name, rank
    FROM crystal_ranks
  """
  async with AgimusDB(dictionary=True) as db:
    return await db.query(sql)

async def db_get_crystals_by_rarity(rarity_rank: int):
  sql = """
    SELECT ct.*, cr.emoji, cr.name AS rarity_name
    FROM crystal_types ct
    JOIN crystal_ranks cr ON ct.rarity_rank = cr.rarity_rank
    WHERE ct.rarity_rank = %s
    ORDER BY ct.name ASC
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (rarity_rank,))
    return await db.fetchall()


async def db_get_crystal_rarity_weights():
  sql = """
    SELECT rarity_rank, drop_chance
    FROM crystal_ranks
    ORDER BY rarity_rank DESC
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql)
    return await db.fetchall()


async def db_select_random_crystal_type_by_rarity_rank(rarity_rank: str) -> dict | None:
  sql = """
    SELECT id, name, effect
    FROM crystal_types
    WHERE rarity_rank = %s
    ORDER BY RAND()
    LIMIT 1
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (rarity_rank,))
    return await db.fetchone()

async def db_get_user_attuned_and_harmonized_crystals(discord_id: int) -> list[dict]:
  sql = """
    SELECT
      ci.id AS crystal_instance_id,
      ci.owner_discord_id,
      ci.status AS crystal_status,
      ci.created_at AS crystal_created_at,

      ct.id AS crystal_type_id,
      ct.name AS crystal_name,
      ct.icon,
      ct.description,
      ct.effect,
      ct.rarity_rank,

      cr.name AS rarity_name,
      cr.emoji,
      cr.drop_chance,
      cr.sort_order

    FROM crystal_instances ci
    JOIN crystal_types ct ON ci.crystal_type_id = ct.id
    JOIN crystal_ranks cr ON ct.rarity_rank = cr.rarity_rank
    WHERE ci.owner_discord_id = %s AND NOT ci.status = 'available'
    ORDER BY cr.sort_order ASC, ct.name ASC
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (discord_id,))
    return await db.fetchall()


async def db_get_user_unattuned_crystals(discord_id: int) -> list[dict]:
  sql = """
    SELECT
      ci.id AS crystal_instance_id,
      ci.owner_discord_id,
      ci.status AS crystal_status,
      ci.created_at AS crystal_created_at,

      ct.id AS crystal_type_id,
      ct.name AS crystal_name,
      ct.icon,
      ct.description,
      ct.effect,
      ct.rarity_rank,

      cr.name AS rarity_name,
      cr.emoji,
      cr.drop_chance,
      cr.sort_order

    FROM crystal_instances ci
    JOIN crystal_types ct ON ci.crystal_type_id = ct.id
    JOIN crystal_ranks cr ON ct.rarity_rank = cr.rarity_rank
    WHERE ci.owner_discord_id = %s AND ci.status = 'available'
    ORDER BY cr.sort_order ASC, ct.name ASC
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (discord_id,))
    return await db.fetchall()

async def db_get_user_unattuned_crystal_rarities(user_id: int) -> list[dict]:
  sql = """
    SELECT
      cr.name,
      cr.emoji,
      cr.rarity_rank,
      cr.sort_order,
      COUNT(*) AS count
    FROM crystal_instances ci
    JOIN crystal_types ct ON ci.crystal_type_id = ct.id
    JOIN crystal_ranks cr ON ct.rarity_rank = cr.rarity_rank
    WHERE ci.owner_discord_id = %s
      AND ci.status = 'available'
    GROUP BY cr.name, cr.emoji, cr.rarity_rank, cr.sort_order
    ORDER BY cr.sort_order ASC
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (user_id,))
    return await db.fetchall()

async def db_get_unattuned_crystals_by_rarity(user_id: int, rarity_name: str) -> list[dict]:
  sql = """
    SELECT
      ci.id AS crystal_instance_id,
      ci.owner_discord_id,
      ci.status,

      ct.id AS crystal_type_id,
      ct.name AS crystal_name,
      ct.effect,
      ct.description,
      ct.icon,
      ct.rarity_rank,

      cr.name AS rarity_name,
      cr.emoji,
      cr.drop_chance,
      cr.sort_order,

      COUNT(*) OVER (PARTITION BY ct.id) AS count

    FROM crystal_instances ci
    JOIN crystal_types ct ON ci.crystal_type_id = ct.id
    JOIN crystal_ranks cr ON ct.rarity_rank = cr.rarity_rank
    WHERE ci.owner_discord_id = %s
      AND ci.status = 'available'
      AND cr.name = %s
    ORDER BY ct.name ASC
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (user_id, rarity_name))
    return await db.fetchall()

async def db_get_unattuned_crystals_by_type(user_id: int, crystal_type_id: int):
  sql = """
    SELECT
      ci.id AS crystal_instance_id,
      ci.owner_discord_id,
      ci.status,

      ct.id AS crystal_type_id,
      ct.name AS crystal_name,
      ct.description,
      ct.effect,
      ct.rarity_rank,

      cr.name AS rarity_name,
      cr.emoji

    FROM crystal_instances ci
    JOIN crystal_types ct ON ci.crystal_type_id = ct.id
    JOIN crystal_ranks cr ON ct.rarity_rank = cr.rarity_rank
    WHERE ci.owner_discord_id = %s
      AND ci.status = 'available'
      AND ct.id = %s
    ORDER BY ci.created_at ASC
    LIMIT 1
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (user_id, crystal_type_id))
    return await db.fetchall()

async def db_get_available_crystal_types():
  sql = """
    SELECT c.*, r.emoji, r.drop_chance
    FROM crystal_types c
    JOIN crystal_ranks r ON c.rarity_rank = r.rarity_rank
    ORDER BY c.rarity_rank ASC, c.name ASC
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql)
    return await db.fetchall()

async def db_get_crystal_by_type_id(crystal_type_id: int) -> dict | None:
  sql = """
    SELECT ct.*, cr.name AS rarity_name, cr.emoji
    FROM crystal_types ct
    JOIN crystal_ranks cr ON ct.rarity_rank = cr.rarity_rank
    WHERE ct.id = %s
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (crystal_type_id,))
    return await db.fetchone()

# Attunement / Harmonization Queries
async def db_attune_crystal_to_badge_instance(instance_id: int, crystal_name: str = None):
  if not crystal_name:
    return None

  async with AgimusDB(dictionary=True) as db:
    sql = "SELECT id FROM crystal_types WHERE name = %s"
    await db.execute(sql, (crystal_name,))
    crystal_type = await db.fetchone()
    if not crystal_type:
      raise RuntimeError(f"Crystal type '{crystal_name}' not found")

    sql = "SELECT id FROM badge_crystals WHERE badge_instance_id = %s AND crystal_type_id = %s"
    await db.execute(sql, (instance_id, crystal_type["id"]))
    if await db.fetchone():
      return None

    sql = "INSERT INTO badge_crystals (badge_instance_id, crystal_type_id) VALUES (%s, %s)"
    await db.execute(sql, (instance_id, crystal_type["id"]))
    crystal_id = db.lastrowid

    sql = "SELECT * FROM badge_crystals WHERE id = %s"
    await db.execute(sql, (crystal_id,))
    return await db.fetchone()


async def db_set_harmonized_crystal(instance_id: int, crystal_id: int):
  sql = "UPDATE badge_instances SET active_crystal_id = %s WHERE id = %s"
  async with AgimusDB() as db:
    await db.execute(sql, (crystal_id, instance_id))


# Crystal Pattern Buffer (Credits)

async def db_get_user_crystal_buffer_count(user_id: int) -> int:
  sql = "SELECT buffer_count FROM crystal_pattern_buffers WHERE user_discord_id = %s"
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (user_id,))
    row = await db.fetchone()
    return row['buffer_count'] if row else 0


async def db_increment_user_crystal_buffer(user_id: int, amount=1):
  sql = """
    INSERT INTO crystal_pattern_buffers (user_discord_id, buffer_count)
    VALUES (%s, %s)
    ON DUPLICATE KEY UPDATE buffer_count = buffer_count + %s
  """
  async with AgimusDB() as db:
    await db.execute(sql, (user_id, amount, amount))


async def db_decrement_user_crystal_buffer(user_id: int) -> bool:
  sql = """
    UPDATE crystal_pattern_buffers
    SET buffer_count = buffer_count - 1
    WHERE user_discord_id = %s AND buffer_count > 0
  """
  async with AgimusDB() as db:
    await db.execute(sql, (user_id,))
    return db.rowcount > 0


async def db_set_user_crystal_buffer(user_id: int, amount: int):
  sql = """
    INSERT INTO crystal_pattern_buffers (user_discord_id, buffer_count)
    VALUES (%s, %s)
    ON DUPLICATE KEY UPDATE buffer_count = %s
  """
  async with AgimusDB() as db:
    await db.execute(sql, (user_id, amount, amount))


# Replicator Helpers

async def db_get_user_unattuned_crystal_count(user_id: int) -> int:
  sql = """
    SELECT COUNT(*) AS count
    FROM crystal_instances
    WHERE owner_discord_id = %s AND status = 'available'
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (user_id,))
    row = await db.fetchone()
    return row['count'] if row else 0


async def db_get_user_attuned_badge_count(user_id: int) -> int:
  sql = """
    SELECT COUNT(DISTINCT b.badge_instance_id) AS count
    FROM badge_crystals AS b
    JOIN badge_instances AS i ON b.badge_instance_id = i.id
    WHERE i.owner_discord_id = %s
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (user_id,))
    row = await db.fetchone()
    return row['count'] if row else 0
