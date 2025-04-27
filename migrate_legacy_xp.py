# migrate_legacy_xp.py
# One-time migration script to snapshot legacy XP/Level into legacy_xp_records

import asyncio
import argparse
import os
import aiomysql
import logging

async def migrate_legacy_xp(dry_run=False, log_file=None):
  # Setup logging
  log_formatter = logging.Formatter("%(asctime)s - %(message)s")
  logger = logging.getLogger()
  logger.setLevel(logging.INFO)

  console_handler = logging.StreamHandler()
  console_handler.setFormatter(log_formatter)
  logger.addHandler(console_handler)

  if log_file:
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)

  # Connect to DB
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
      logger.info("BEGINNING LEGACY XP MIGRATION")

      await cur.execute("SELECT discord_id, level, xp FROM users WHERE xp > 0")
      user_rows = await cur.fetchall()

      logger.info(f"Found {len(user_rows)} users to migrate.")

      migrated = 0
      skipped = 0

      for row in user_rows:
        user_id = row['discord_id']
        legacy_level = row['level'] or 1
        legacy_xp = row['xp'] or 0

        logger.info(f"Migrating User {user_id}: Level {legacy_level}, XP {legacy_xp}")

        if not dry_run:
          await cur.execute(
            """
            INSERT INTO legacy_xp_records (user_discord_id, legacy_level, legacy_xp)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
              legacy_level = VALUES(legacy_level),
              legacy_xp = VALUES(legacy_xp)
            """,
            (user_id, legacy_level, legacy_xp)
          )

        migrated += 1

      if not dry_run:
        await conn.commit()
        logger.info(f"✅ Successfully migrated {migrated} user records and committed changes.")
      else:
        logger.info(f"✅ Dry Run: Would have migrated {migrated} user records. No changes made.")

  except Exception as e:
    await conn.rollback()
    logger.error(f"❌ Migration failed! Rolled back. Error: {e}")
  finally:
    conn.close()

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--dry-run', action='store_true', help='Run without modifying the database')
  parser.add_argument('--log-file', type=str, help='Optional path to log file', default=None)
  args = parser.parse_args()

  asyncio.run(migrate_legacy_xp(dry_run=args.dry_run, log_file=args.log_file))
