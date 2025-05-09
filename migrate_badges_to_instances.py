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
    autocommit=False
  )

  try:
    async with conn.cursor(aiomysql.DictCursor) as cur:
      print("BEGINNING MIGRATION TRANSACTION")

      # ---------------------------
      # 1. MIGRATE BADGES
      # ---------------------------
      print("... Loading Badge Rows ...")
      await cur.execute("SELECT user_discord_id, badge_filename, locked FROM badges")
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
            VALUES (%s, %s, %s, %s)
            """,
            (badge_info_id, user_discord_id, locked, user_discord_id)
          )
          badge_instance_id = cur.lastrowid

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

          migrated += 1
        else:
          print(f"[Dry Run] Would insert badge_instance for '{badge_filename}'")

      print(f"✅ {'Would have migrated' if dry_run else 'Migrated'} {migrated} badge records ({skipped} skipped)")

      # ---------------------------
      # 2. MIGRATE PRIME WISHLISTS
      # ---------------------------
      print("... Migrating badge_wishlists -> badge_instances_wishlists ...")
      await cur.execute("SELECT user_discord_id, badge_filename, time_created FROM badge_wishlists")
      rows = await cur.fetchall()

      migrated = 0
      for row in rows:
        user_id       = row["user_discord_id"]
        filename      = row["badge_filename"]
        original_time = row["time_created"]

        # resolve badge_info_id
        await cur.execute(
          "SELECT id FROM badge_info WHERE badge_filename = %s",
          (filename,),
        )
        info = await cur.fetchone()
        if not info:
          print(f"[Wishlist] Skipping unknown badge_filename: {filename}")
          continue

        if not dry_run:
          await cur.execute(
            """
            INSERT INTO badge_instances_wishlists
              (user_discord_id, badge_info_id, time_added)
            VALUES (%s, %s, %s) AS new
            ON DUPLICATE KEY UPDATE
              time_added = LEAST(badge_instances_wishlists.time_added, new.time_added)
            """,
            (user_id, info["id"], original_time),
          )

        migrated += 1

      print(f"✅ {'Would have migrated' if dry_run else 'Migrated'} {migrated} prime‑wishlist entries")

      # ---------------------------
      # 4. MIGRATE TAG ASSOCIATIONS
      # ---------------------------
      print("... Migrating badge tag associations ...")
      await cur.execute(
        '''
        SELECT t.badge_tags_id, b.user_discord_id, b.badge_filename
        FROM badge_tags_associations t
        JOIN badges b ON t.badges_id = b.id
        '''
      )
      tag_rows = await cur.fetchall()

      tags_migrated = 0
      for row in tag_rows:
        badge_filename = row["badge_filename"]
        user_id = row["user_discord_id"]
        badge_tags_id = row["badge_tags_id"]

        await cur.execute(
          "SELECT id FROM badge_info WHERE badge_filename = %s",
          (badge_filename,)
        )
        info = await cur.fetchone()
        if not info:
          print(f"[Tags] Skipping: No badge_info found for {badge_filename}")
          continue

        if not dry_run:
          await cur.execute(
            """
            INSERT IGNORE INTO badge_info_tags_associations (user_discord_id, badge_info_id, badge_tags_id)
            VALUES (%s, %s, %s)
            """,
            (user_id, info["id"], badge_tags_id)
          )
        tags_migrated += 1

      print(f"✅ {'Would have migrated' if dry_run else 'Migrated'} {tags_migrated} badge tag associations")

      # ---------------------------
      # 5. MIGRATE PROFILE FEATURED BADGES
      # ---------------------------
      print("... Migrating profile_badges → profile_badge_instances ...")
      await cur.execute("SELECT user_discord_id, badge_filename FROM profile_badges")
      rows = await cur.fetchall()

      migrated = 0
      skipped = 0

      for row in rows:
        user_id = row["user_discord_id"]
        filename = row["badge_filename"]

        if not filename:
          continue

        # Resolve badge_info_id
        await cur.execute("SELECT id FROM badge_info WHERE badge_filename = %s", (filename,))
        info = await cur.fetchone()
        if not info:
          print(f"[Profile Badge] Skipping: Unknown badge filename '{filename}'")
          skipped += 1
          continue
        badge_info_id = info["id"]

        # Try to locate Standard prestige badge_instance for this user
        await cur.execute(
          """
          SELECT id FROM badge_instances
          WHERE badge_info_id = %s AND owner_discord_id = %s AND prestige_level = 0
          """,
          (badge_info_id, user_id)
        )
        instance = await cur.fetchone()
        if not instance:
          print(f"[Profile Badge] Skipping: No Standard badge_instance found for {filename} and user {user_id}")
          skipped += 1
          continue

        badge_instance_id = instance["id"]

        if not dry_run:
          await cur.execute(
            """
            REPLACE INTO profile_badge_instances (user_discord_id, badge_instance_id)
            VALUES (%s, %s)
            """,
            (user_id, badge_instance_id)
          )
        else:
          print(f"[Dry Run] Would migrate profile badge: {filename} → instance {badge_instance_id}")

        migrated += 1

      print(f"✅ {'Would have migrated' if dry_run else 'Migrated'} {migrated} profile badge entries ({skipped} skipped)")

      if not dry_run:
        await conn.commit()
        print("✅ COMMIT COMPLETE")
      else:
        print("✅ Dry Run: NO CHANGES MADE")

  except Exception as e:
    await conn.rollback()
    print(f"❌ Migration failed! ROLLED BACK.\nError: {e}")
  finally:
    conn.close()


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--dry-run', action='store_true', help='Run without modifying the database')
  args = parser.parse_args()
  asyncio.run(migrate_badges(dry_run=args.dry_run))
