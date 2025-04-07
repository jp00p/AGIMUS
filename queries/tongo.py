from typing import Optional

from common import *

# --- Game Lifecycle ---

async def db_create_tongo_game(chair_user_id: int) -> int:
  query = """
    INSERT INTO tongo_games (chair_user_id)
    VALUES (%s)
  """
  async with AgimusDB(dictionary=True) as query:
    await query.execute(query, (chair_user_id,))
    return query.lastrowid


async def db_update_game_status(game_id: int, status: str):
  query = """
    UPDATE tongo_games SET status = %s WHERE id = %s
  """
  async with AgimusDB() as db:
    await db.execute(query, (status, game_id))


async def db_get_open_game():
  query = """
    SELECT * FROM tongo_games WHERE status = 'open' ORDER BY created_at DESC LIMIT 1
  """
  async with AgimusDB() as db:
    return await db.fetchone(query)


async def db_get_latest_game():
  query = """
    SELECT * FROM tongo_games ORDER BY created_at DESC LIMIT 1
  """
  async with AgimusDB() as db:
    return await db.fetchone(query)


# --- Game Players ---

async def db_add_game_player(game_id: int, user_id: int, liability_mode: str):
  query = """
    INSERT INTO tongo_game_players (game_id, user_discord_id, liability_mode)
    VALUES (%s, %s, %s)
  """
  async with AgimusDB() as db:
    await db.execute(query, (game_id, user_id, liability_mode))


async def db_get_players_for_game(game_id: int):
  query = """
    SELECT user_discord_id, liability_mode FROM tongo_game_players
    WHERE game_id = %s
  """
  async with AgimusDB() as db:
    return await db.fetchall(query, (game_id,))


async def db_is_user_in_game(game_id: int, user_id: int) -> bool:
  query = """
    SELECT 1
    FROM tongo_game_players
    WHERE tongo_game_id = %s AND user_discord_id = %s
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
    rows = await db.fetchall(query, (game_id,))
    return [int(row['user_discord_id']) for row in rows]


# --- Continuum ---

async def db_add_to_continuum(badge_info_id: int, source_instance_id: int, user_id: int):
  query = """
    INSERT INTO tongo_continuum (badge_info_id, source_instance_id, thrown_by_user_id)
    VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE source_instance_id = VALUES(source_instance_id), thrown_by_user_id = VALUES(thrown_by_user_id)
  """
  async with AgimusDB() as db:
    await db.execute(query, (badge_info_id, source_instance_id, user_id))


async def db_get_continuum_badge_ids():
  query = """
    SELECT badge_info_id FROM tongo_continuum
  """
  async with AgimusDB() as db:
    rows = await db.fetchall(query)
    return [row['badge_info_id'] for row in rows]


async def db_remove_from_continuum(badge_info_id: int):
  query = """
    DELETE FROM tongo_continuum WHERE badge_info_id = %s
  """
  async with AgimusDB() as db:
    await db.execute(query, (badge_info_id,))


# --- Distribution ---
async def db_update_instance_owner(instance_id: int, user_id: int):
  query = """
    UPDATE badge_instances
    SET user_discord_id = %s
    WHERE id = %s
  """
  async with AgimusDB() as db:
    await db.execute(query, (user_id, instance_id))


# --- Rewards ---



async def db_add_game_reward(game_id: int, user_id: int, badge_instance_id: int, crystal_id: Optional[int] = None):
  query = """
    INSERT INTO tongo_game_rewards (game_id, user_discord_id, badge_instance_id, crystal_id)
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
  async with AgimusDB() as db:
    return await db.fetchall(query, (game_id,))
