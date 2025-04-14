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
      # 2. MIGRATE WISHLISTS
      # ---------------------------
      print("... Migrating badge wishlists ...")
      await cur.execute("SELECT user_discord_id, badge_filename FROM badge_wishlists")
      wishlist_rows = await cur.fetchall()

      wishlist_migrated = 0
      for row in wishlist_rows:
        user_id = row["user_discord_id"]
        badge_filename = row["badge_filename"]

        await cur.execute("SELECT id FROM badge_info WHERE badge_filename = %s", (badge_filename,))
        badge_info = await cur.fetchone()
        if not badge_info:
          print(f"[Wishlist] Skipping unknown badge filename: {badge_filename}")
          continue

        if not dry_run:
          await cur.execute(
            """
            INSERT IGNORE INTO badge_instance_wishlists (user_discord_id, badge_info_id)
            VALUES (%s, %s)
            """,
            (user_id, badge_info["id"])
          )
        wishlist_migrated += 1

      print(f"✅ {'Would have migrated' if dry_run else 'Migrated'} {wishlist_migrated} wishlist entries")

      # ---------------------------
      # 3. MIGRATE WISHLIST DISMISSALS
      # ---------------------------
      print("... Migrating wishlist dismissals ...")
      await cur.execute("SELECT user_discord_id, match_discord_id, has, wants, time_created FROM wishlist_dismissals")
      dismissal_rows = await cur.fetchall()

      dismissals_migrated = 0
      for row in dismissal_rows:
        if not dry_run:
          await cur.execute(
            """
            INSERT IGNORE INTO badge_instance_wishlist_dismissals (
              user_discord_id,
              match_discord_id,
              has,
              wants,
              time_created
            ) VALUES (%s, %s, %s, %s, %s)
            """,
            (
              row["user_discord_id"],
              row["match_discord_id"],
              row["has"],
              row["wants"],
              row["time_created"]
            )
          )
        dismissals_migrated += 1

      print(f"✅ {'Would have migrated' if dry_run else 'Migrated'} {dismissals_migrated} wishlist dismissal entries")

      # ---------------------------
      # 4. MIGRATE TAG ASSOCIATIONS
      # ---------------------------
      print("... Migrating badge tag associations ...")
      await cur.execute(
        """
        SELECT t.badge_tags_id, b.user_discord_id, b.badge_filename
        FROM badge_tags_associations t
        JOIN badges b ON t.badges_id = b.id
        """
      )
      tag_rows = await cur.fetchall()

      tags_migrated = 0
      for row in tag_rows:
        badge_filename = row["badge_filename"]
        user_id = row["user_discord_id"]
        badge_tags_id = row["badge_tags_id"]

        await cur.execute("""
          SELECT inst.id FROM badge_instances inst
          JOIN badge_info info ON inst.badge_info_id = info.id
          WHERE info.badge_filename = %s AND inst.owner_discord_id = %s AND inst.active = TRUE
        """, (badge_filename, user_id))
        badge_instance = await cur.fetchone()

        if not badge_instance:
          print(f"[Tags] Skipping: No active instance found for {user_id} / {badge_filename}")
          continue

        if not dry_run:
          await cur.execute(
            """
            INSERT IGNORE INTO badge_instances_tags_associations (badge_instance_id, badge_tags_id)
            VALUES (%s, %s)
            """,
            (badge_instance["id"], badge_tags_id)
          )
        tags_migrated += 1

      print(f"✅ {'Would have migrated' if dry_run else 'Migrated'} {tags_migrated} badge tag associations")

      # ---------------------------
      # 5. MIGRATE CAROUSEL POSITIONS
      # ---------------------------
      print("... Migrating carousel positions ...")
      await cur.execute("SELECT user_discord_id, badge_filename, last_modified FROM tags_carousel_position")
      carousel_rows = await cur.fetchall()

      carousel_migrated = 0
      for row in carousel_rows:
        badge_filename = row["badge_filename"]
        user_id = row["user_discord_id"]
        last_modified = row["last_modified"]

        await cur.execute("""
          SELECT inst.id FROM badge_instances inst
          JOIN badge_info info ON inst.badge_info_id = info.id
          WHERE info.badge_filename = %s AND inst.owner_discord_id = %s AND inst.active = TRUE
        """, (badge_filename, user_id))
        badge_instance = await cur.fetchone()

        if not badge_instance:
          print(f"[Carousel] Skipping: No active instance found for {user_id} / {badge_filename}")
          continue

        if not dry_run:
          await cur.execute(
            """
            INSERT IGNORE INTO badge_instances_tags_carousel_position (
              user_discord_id, badge_instance_id, last_modified
            ) VALUES (%s, %s, %s)
            """,
            (user_id, badge_instance["id"], last_modified)
          )
        carousel_migrated += 1

      print(f"✅ {'Would have migrated' if dry_run else 'Migrated'} {carousel_migrated} carousel positions")

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
