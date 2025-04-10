# migrate_badges_to_instances.py
# Standalone migration script to convert old badge records into badge_instances + crystals

import asyncio
import argparse
import os
import aiomysql

async def migrate_badges(dry_run=False):
  conn = await aiomysql.connect(
    host=os.environ.get("DB_HOST", "localhost"),
    port=int(os.environ.get("DB_PORT", 3306)),
    user=os.environ.get("DB_USER", "root"),
    password=os.environ.get("DB_PASS", ""),
    db=os.environ.get("DB_NAME", "agimus"),
    autocommit=True
  )

  async with conn.cursor(aiomysql.DictCursor) as cur:
    await cur.execute("SELECT id FROM crystal_types WHERE name = 'Dilithium'")
    row = await cur.fetchone()
    if not row:
      raise RuntimeError("Dilithium crystal_type not found")
    dilithium_id = row["id"]

    print("... Loading Badge Rows ...")
    await cur.execute("SELECT user_discord_id, badge_filename, locked FROM badges WHERE user_discord_id = 1196611546776879214")
    badge_rows = await cur.fetchall()
    print("... Badge Rows Loaded ...")

    skipped = 0
    migrated = 0

    for badge_row in badge_rows:
      user_discord_id = badge_row["user_discord_id"]
      badge_filename = badge_row["badge_filename"]
      locked = badge_row["locked"]

      await cur.execute("SELECT id FROM badge_info WHERE badge_filename = %s", (badge_filename,))
      row = await cur.fetchone()
      if not row:
        print(f"Skipping unknown badge filename: {badge_filename}")
        continue
      badge_info_id = row["id"]

      # Re-check if this instance already exists to avoid duplicate key error
      await cur.execute(
        "SELECT id FROM badge_instances WHERE owner_discord_id = %s AND badge_info_id = %s",
        (user_discord_id, badge_info_id)
      )
      existing = await cur.fetchone()
      if existing:
        print(f"[Skip] Badge instance already exists for {user_discord_id} / {badge_filename}")
        skipped += 1
        continue

      print(f"> Migrating User {user_discord_id}: {badge_filename}")

      if not dry_run:
        await cur.execute(
          """
          INSERT INTO badge_instances (badge_info_id, owner_discord_id, locked, origin_user_id)
          VALUES (%s, %s, %s)
          """,
          (badge_info_id, user_discord_id, locked, user_discord_id)
        )
        badge_instance_id = cur.lastrowid

        # Log the initial acquisition to badge_instance_history
        await cur.execute(
          """
          INSERT INTO badge_instance_history (
            badge_instance_id,
            from_user_id,
            to_user_id,
            event_type
          ) VALUES (%s, %s, %s, %s)
          """,
          (badge_instance_id, None, user_discord_id, 'epoch')
        )

        # Give everyone a Dilithium crystal by default
        await cur.execute(
          """
          INSERT INTO badge_crystals (badge_instance_id, crystal_type_id)
          VALUES (%s, %s)
          """,
          (badge_instance_id, dilithium_id)
        )

        migrated += 1
      else:
        print(f"[Dry Run] Would insert badge_instance for '{badge_filename}' and attach Dilithium crystal")

    print(f"✅ {'Would have migrated' if dry_run else 'Migrated'} {migrated} badge records ({skipped} skipped)")

  conn.close()

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--dry-run', action='store_true', help='Run without modifying the database')
  args = parser.parse_args()
  asyncio.run(migrate_badges(dry_run=args.dry_run))
