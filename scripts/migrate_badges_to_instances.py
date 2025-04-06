# migrate_badges_to_instances.py
# Standalone migration script to convert old badge records into badge_instances + crystals

import asyncio
import argparse
from utils.database import AgimusDB

async def migrate_badges(dry_run=False):
  async with AgimusDB(dictionary=True) as query:
    await query.execute("SELECT id FROM crystal_types WHERE name = 'Dilithium'")
    row = await query.fetchone()
    if not row:
      raise RuntimeError("Dilithium crystal_type not found")
    dilithium_id = row["id"]

    print("... Loading Badge Rows ...")
    await query.execute("SELECT user_discord_id, badge_filename, locked FROM badges ORDER BY user_discord_id")
    badge_rows = await query.fetchall()
    print("... Badge Rows Loaded ...")

    for badge_row in badge_rows:
      user_discord_id = badge_row["user_discord_id"]
      badge_filename = badge_row["badge_filename"]
      locked = badge_row["locked"]

      print(f"> Migrating User {user_discord_id}: {badge_filename}")

      await query.execute("SELECT id FROM badge_info WHERE filename = %s", (badge_filename,))
      row = await query.fetchone()
      if not row:
        print(f"Skipping unknown badge filename: {badge_filename}")
        continue
      badge_info_id = row["id"]

      if not dry_run:
        await query.execute(
          """
          INSERT INTO badge_instances (badge_info_id, owner_discord_id, locked)
          VALUES (%s, %s, %s)
          """,
          (badge_info_id, user_discord_id, locked)
        )
        badge_instance_id = query.lastrowid

        await query.execute(
          """
          INSERT INTO badge_crystals (badge_instance_id, crystal_type_id)
          VALUES (%s, %s)
          """,
          (badge_instance_id, dilithium_id)
        )
        crystal_id = query.lastrowid

        await query.execute(
          "UPDATE badge_instances SET preferred_crystal_id = %s WHERE id = %s",
          (crystal_id, badge_instance_id)
        )
      else:
        print(f"[Dry Run] Would insert badge_instance for '{badge_filename}' and attach Dilithium crystal")

    print(f"✅ {'Would have migrated' if dry_run else 'Migrated'} {len(badge_rows)} badge records")

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--dry-run', action='store_true', help='Run without modifying the database')
  args = parser.parse_args()
  asyncio.run(migrate_badges(dry_run=args.dry_run))
