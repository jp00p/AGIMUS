# eschelon_qa_test.py

import asyncio
from common import AgimusDB
from handlers.eschelon_xp import award_xp, get_user_eschelon_progress
from handlers.eschelon_rewards import award_possible_crystal_buffer_pattern
from utils.badge_utils import db_get_user_badge_instances

# --- Monkeypatch Setup ---
REAL_AgimusDB = AgimusDB  # Save original

class SharedAgimusDB:
  def __init__(self, connection):
    self.connection = connection

  async def __aenter__(self):
    return self.connection

  async def __aexit__(self, exc_type, exc, tb):
    pass

async def run_eschelon_qa_test(user_id: int, num_levelups: int = 50):
  async with REAL_AgimusDB(dictionary=True) as shared_db:
    print(f"\n🚀 Starting Eschelon QA Simulation for user {user_id}")
    print(f"Beginning simulated transaction...\n")

    await shared_db.execute("START TRANSACTION;")

    # Monkeypatch AgimusDB to always reuse shared connection
    import common
    common.AgimusDB = lambda dictionary=True: shared_db

    level_ups = 0
    badges_awarded = 0
    buffers_awarded = 0

    try:
      for _ in range(num_levelups):
        progress = await get_user_eschelon_progress(user_id)
        current_level = progress['current_level'] if progress else 1
        xp_needed = xp_required_for_level(current_level)

        new_level = await award_xp(user_id, xp_needed, reason="admin")
        if new_level:
          level_ups += 1
          badges = await db_get_user_badge_instances(user_id)
          badges_awarded = len(badges)

          success = await award_possible_crystal_buffer_pattern(user_id)
          if success:
            buffers_awarded += 1

        await asyncio.sleep(0.05)

      print(f"\n✅ QA Simulation Completed Successfully!")
      print(f"Level-Ups Simulated: {level_ups}")
      print(f"Total Badges Awarded: {badges_awarded}")
      print(f"Total Buffer Insurance Awards: {buffers_awarded}")

    finally:
      print("\nRolling back all simulated changes...")
      await shared_db.execute("ROLLBACK;")
      print("🎯 Database rolled back. No changes persisted.\n")
      # Restore original AgimusDB after test
      common.AgimusDB = REAL_AgimusDB


def xp_required_for_level(level: int) -> int:
  if level <= 0:
    return 0
  if level > 170:
    return 420
  t = (level - 1) / (170 - 1)
  ease = 3 * (t**2) - 2 * (t**3)
  return int(69 + (420 - 69) * ease)


if __name__ == "__main__":
  import sys

  if len(sys.argv) < 2:
    print("Usage: python eschelon_qa_test.py <user_id> [number_of_levelups]")
    sys.exit(1)

  user_id = int(sys.argv[1])
  num_levelups = int(sys.argv[2]) if len(sys.argv) > 2 else 50

  asyncio.run(run_eschelon_qa_test(user_id, num_levelups))
