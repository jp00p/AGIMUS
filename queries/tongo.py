from typing import Optional

from common import *

from queries.common import BADGE_INSTANCE_COLUMNS

# --- Game Lifecycle ---

async def db_create_tongo_game(chair_user_id: int) -> int:
  query = """
    INSERT INTO tongo_games (chair_user_id, status)
    VALUES (%s, 'open')
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(query, (chair_user_id,))
    return db.lastrowid


async def db_update_game_status(game_id: int, status: str):
  query = """
    UPDATE tongo_games SET status = %s WHERE id = %s
  """
  async with AgimusDB() as db:
    await db.execute(query, (status, game_id))


async def db_get_open_game():
  query = '''
    SELECT * FROM tongo_games
    WHERE status = 'open'
    ORDER BY created_at DESC
    LIMIT 1
  '''
  async with AgimusDB(dictionary=True) as db:
    await db.execute(query)
    return await db.fetchone()


# --- Game Players ---

async def db_add_game_player(game_id: int, user_id: int):
  query = """
    INSERT INTO tongo_game_players (game_id, user_discord_id)
    VALUES (%s, %s)
  """
  async with AgimusDB() as db:
    await db.execute(query, (game_id, user_id))


async def db_get_players_for_game(game_id: int):
  query = """
    SELECT user_discord_id FROM tongo_game_players
    WHERE game_id = %s
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(query, (game_id,))
    return await db.fetchall()

async def db_remove_player_from_game(game_id: int, user_id: int):
  async with AgimusDB() as db:
    sql = '''
      DELETE FROM tongo_game_players
      WHERE game_id = %s AND user_discord_id = %s
    '''
    await db.execute(sql, (game_id, user_id))

async def db_is_user_in_game(game_id: int, user_id: int) -> bool:
  query = """
    SELECT 1
    FROM tongo_game_players
    WHERE game_id = %s AND user_discord_id = %s
    LIMIT 1
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(query, (game_id, user_id))
    return await db.fetchone() is not None


async def db_get_all_game_player_ids(game_id: int) -> list[int]:
  query = """
    SELECT user_discord_id
    FROM tongo_game_players
    WHERE game_id = %s
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(query, (game_id,))
    rows = await db.fetchall()
    return [int(row['user_discord_id']) for row in rows]


# --- Continuum ---
async def db_add_to_continuum(source_instance_id: int, user_id: Optional[int]):
  query = """
    INSERT IGNORE INTO tongo_continuum (source_instance_id, thrown_by_user_id)
    VALUES (%s, %s)
  """
  async with AgimusDB() as db:
    await db.execute(query, (source_instance_id, user_id))

async def db_get_continuum_badge_info_prestige_pairs() -> set[tuple[int, int]]:
  """
  Returns all (badge_info_id, prestige_level) pairs currently in the continuum.
  """
  query = """
    SELECT b.badge_info_id, b.prestige_level
    FROM tongo_continuum t
    JOIN badge_instances b ON t.source_instance_id = b.id
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(query)
    rows = await db.fetchall()
    return {(r['badge_info_id'], r['prestige_level']) for r in rows}


async def db_get_continuum_badge_info_ids_at_prestige(prestige: int | None = None) -> set[int]:
  sql = """
    SELECT DISTINCT b.badge_info_id
    FROM tongo_continuum t
    JOIN badge_instances b ON t.source_instance_id = b.id
  """
  params = []
  if prestige is not None:
    sql += " WHERE b.prestige_level = %s"
    params.append(prestige)

  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, params)
    rows = await db.fetchall()
    return {row['badge_info_id'] for row in rows}


async def db_get_grouped_continuum_badge_info_ids_by_prestige() -> set[tuple[int, int]]:
  query = """
    SELECT b.badge_info_id, b.prestige_level
    FROM tongo_continuum t
    JOIN badge_instances b ON t.source_instance_id = b.id
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(query)
    rows = await db.fetchall()
    return {(row['badge_info_id'], row['prestige_level']) for row in rows}


async def db_remove_from_continuum(source_instance_id: int):
  query = """
    DELETE FROM tongo_continuum WHERE source_instance_id = %s
  """
  async with AgimusDB() as db:
    await db.execute(query, (source_instance_id,))


async def db_get_full_continuum_badges():
  """
  Retrieve enriched badge_instance records from the Tongo continuum.
  Includes the badge_info, instance, and crystal data, plus Tongo-specific fields:
    - source_instance_id: the original badge_instance_id thrown into the pot
    - thrown_by_user_id: who threw it in
  """
  query = f"""
    SELECT
      {BADGE_INSTANCE_COLUMNS},
      t_c.source_instance_id,
      t_c.thrown_by_user_id
    FROM tongo_continuum AS t_c
    JOIN badge_instances AS b ON t_c.source_instance_id = b.id
    JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
    LEFT JOIN badge_crystals AS c ON b.active_crystal_id = c.id
    LEFT JOIN crystal_instances AS ci ON c.crystal_instance_id = ci.id
    LEFT JOIN crystal_types AS t ON ci.crystal_type_id = t.id
    ORDER BY b_i.badge_name ASC
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(query)
    return await db.fetchall()


# -- Liquidation

async def db_liquidate_badge_instance(instance_id: int):
  # Fetch old owner (if any)
  query_owner = """
    SELECT owner_discord_id
    FROM badge_instances
    WHERE id = %s
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(query_owner, (instance_id,))
    old = await db.fetchone()
    old_owner = old['owner_discord_id'] if old else None

  # Null ownership + set to 'liquidated'
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


# --- Rewards ---
async def db_add_game_reward(game_id: int, user_id: int, badge_instance_id: int, crystal_id: Optional[int] = None):
  query = """
    INSERT IGNORE INTO tongo_game_rewards (game_id, user_discord_id, badge_instance_id, crystal_id)
    VALUES (%s, %s, %s, %s)
  """
  async with AgimusDB() as db:
    await db.execute(query, (game_id, user_id, badge_instance_id, crystal_id))


async def db_get_rewards_for_game(game_id: int):
  query = """
    SELECT user_discord_id, badge_instance_id, crystal_id
    FROM tongo_game_rewards
    WHERE game_id = %s
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(query, (game_id,))
    return await db.fetchall()


# --- "History" ---
async def db_get_throws_for_game(game_id: int, created_at: datetime) -> list[dict]:
  """
  Returns all badges thrown into the Tongo continuum during a specific game,
  reconstructed by matching `tongo_risk` events from badge_instance_history.

  Args:
    game_id (int): The ID of the Tongo game.
    created_at (datetime): The timestamp when the game was created.

  Returns:
    list[dict]: A list of dicts, each containing:
      - badge_instance_id
      - from_user_id
      - occurred_at
      - badge_name
  """
  query = """
    SELECT
      h.badge_instance_id,
      h.from_user_id,
      h.occurred_at,
      bi.badge_name
    FROM badge_instance_history AS h
    JOIN badge_instances AS b ON h.badge_instance_id = b.id
    JOIN badge_info AS bi ON b.badge_info_id = bi.id
    WHERE h.event_type = 'tongo_risk'
      AND h.occurred_at >= %s
      AND h.from_user_id IN (
        SELECT user_discord_id FROM tongo_game_players WHERE game_id = %s
      )
  """
  async with AgimusDB(dictionary=True) as db:
    await db.execute(query, (created_at, game_id))
    return await db.fetchall()


# --- Dividends ---
async def db_get_tongo_dividends(user_id: int) -> dict | None:
  sql = "SELECT * FROM tongo_dividends WHERE user_discord_id = %s"
  async with AgimusDB(dictionary=True) as db:
    await db.execute(sql, (user_id,))
    return await db.fetchone()

async def db_increment_tongo_dividends(user_id: int, amount: int = 1):
  sql = """
    INSERT INTO tongo_dividends
    SET user_discord_id = %s,
        current_balance = %s,
        lifetime_earned = %s
    ON DUPLICATE KEY UPDATE
      current_balance = current_balance + %s,
      lifetime_earned = lifetime_earned + %s
  """
  async with AgimusDB() as db:
    await db.execute(sql, (user_id, amount, amount, amount, amount))


async def db_decrement_user_tongo_dividends(user_id: int, amount: int):
  sql = """
    UPDATE tongo_dividends
    SET current_balance = GREATEST(current_balance - %s, 0)
    WHERE user_discord_id = %s
  """
  async with AgimusDB() as db:
    await db.execute(sql, (amount, user_id))
